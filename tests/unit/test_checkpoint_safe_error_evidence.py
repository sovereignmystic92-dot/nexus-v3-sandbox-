import io
import json
import unittest
import urllib.error
from nexus_sandbox.notion_checkpoint_api import NotionRequest, RequestFailure, request_error_evidence
import test_notion_checkpoint_write_probe as existing

class SafeEvidenceTests(unittest.TestCase):
    def test_http_status_is_retained_without_body_url_headers_or_message(self):
        for status in (401,403,429,500):
            client=NotionRequest(existing.probe.AUDIT_ID,'private-token','2022-06-28',write_enabled=True)
            class Opener:
                def open(self,*args,**kwargs):
                    raise urllib.error.HTTPError('https://private-url',status,'private-message',
                        {'Authorization':'private-header'},io.BytesIO(b'private-body'))
            client._opener=Opener()
            with self.assertRaises(RequestFailure) as caught:
                client('PATCH','/v1/blocks/'+existing.probe.AUDIT_ID+'/children',{})
            value=request_error_evidence(caught.exception)
            self.assertEqual(value,dict(category='HTTP_ERROR',http_status=status))
            self.assertNotIn('private',str(caught.exception)+json.dumps(value))
    def test_malformed_status_and_unknown_errors_never_echo(self):
        for status in ('private',True,399,600,{},None):
            value=request_error_evidence(RequestFailure('HTTP_ERROR',status))
            self.assertIsNone(value['http_status'])
            self.assertNotIn('private',json.dumps(value))
        error=RequestFailure('private',403)
        self.assertEqual(request_error_evidence(error),dict(category='UNKNOWN',http_status=None))
        self.assertEqual(request_error_evidence(RuntimeError('private-token')),dict(category='UNKNOWN',http_status=None))
    def test_append_http_error_and_absence_remain_uncertain_without_replay(self):
        fixture=existing.WriteProbeTests();fixture.setUp()
        def request(method,path,payload):
            if method=='PATCH':
                fixture.calls.append((method,path,payload))
                raise RequestFailure('HTTP_ERROR',403)
            return fixture.request(method,path,payload)
        result=existing.probe.probe(request,'123','a'*40,allow_write=True)
        self.assertEqual(result['result'],'BLOCKED_UNCERTAIN')
        self.assertEqual(result['write_error'],dict(category='HTTP_ERROR',http_status=403))
        self.assertEqual(result['write_ack'],'UNCERTAIN')
        self.assertEqual(result['readback_result'],'BOUNDED_ABSENCE')
        self.assertEqual(result['failure_stage'],'READBACK')
        self.assertEqual(len(fixture.writes()),1)
    def test_acknowledged_write_then_unavailable_readback_preserves_ack(self):
        fixture=existing.WriteProbeTests();fixture.setUp();written=False
        def request(method,path,payload):
            nonlocal written
            if method=='GET' and written:raise TimeoutError('private-token')
            value=fixture.request(method,path,payload)
            if method=='PATCH':written=True
            return value
        result=existing.probe.probe(request,'123','a'*40,allow_write=True)
        self.assertEqual(result['write_ack'],'RECEIVED')
        self.assertEqual(result['write_outcome'],'ACKNOWLEDGED')
        self.assertEqual(result['checkpoint_state'],'UNKNOWN')
        self.assertEqual(result['readback_result'],'UNKNOWN')
        self.assertEqual(result['observation_error'],dict(category='TIMEOUT',http_status=None))
        self.assertNotIn('private-token',json.dumps(result))
        self.assertEqual(len(fixture.writes()),1)
