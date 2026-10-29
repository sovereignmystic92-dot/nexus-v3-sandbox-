import importlib.util
import json
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('auditprobe',Path(__file__).resolve().parents[2]/'tools/notion_audit_access_probe.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class AuditReadTests(unittest.TestCase):
    def response(self,body=None,status=200):
        body=body if body is not None else dict(object='page',id=module.AUDIT_ID,archived=False,in_trash=False)
        owner=self
        class Response:
            def __init__(self):self.status=status
            def getheader(self,*args):return 'application/json'
            def read(self,n):return json.dumps(body).encode()[:n]
        class Connection:
            def request(self,*args,**kwargs):owner.calls.append((args,kwargs))
            def getresponse(self):return Response()
            def close(self):owner.closed=True
        return lambda *args,**kwargs:Connection()
    def setUp(self):self.calls=[];self.closed=False
    def test_exact_target_one_get_zero_writes(self):
        result=module.probe('synthetic-token',self.response())
        self.assertEqual(self.calls[0][0],('GET','/v1/pages/'+module.AUDIT_ID))
        self.assertEqual(len(self.calls),1);self.assertEqual(result['writes'],0)
        self.assertEqual(result['audit_metadata_access'],'VERIFIED');self.assertTrue(self.closed)
    def test_denial_is_not_retried(self):
        for status in (301,401,403,404,429,503):
            self.calls=[]
            with self.assertRaises(module.Hold):module.probe('synthetic-token',self.response(status=status))
            self.assertEqual(len(self.calls),1);self.assertTrue(self.closed)
    def test_wrong_identity_or_archived_does_not_verify(self):
        for change in (dict(id='00000000000000000000000000000001'),dict(archived=True),dict(in_trash=True)):
            body=dict(object='page',id=module.AUDIT_ID,archived=False,in_trash=False);body.update(change)
            with self.assertRaises(module.Hold):module.probe('synthetic-token',self.response(body))
    def test_bad_token_makes_no_request(self):
        with self.assertRaises(module.Hold):module.probe('bad\nvalue',self.response())
        self.assertEqual(self.calls,[])
