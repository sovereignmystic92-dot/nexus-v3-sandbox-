import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('notion_read_probe', Path(__file__).resolve().parents[2]/'tools/notion_read_probe.py')
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)


class NotionReadProbeTests(unittest.TestCase):
    def setUp(self):
        self.root='1'*32
        self.page={'object':'page','id':self.root,'archived':False,'properties':{
            'title':{'type':'title','title':[{'plain_text':probe.EXPECTED_TITLE}]}}}
        self.status=200;self.calls=[];self.closed=False;self.raw=None
        self.guard=patch.object(probe,'ROOT_COMMITMENT',hashlib.sha256(self.root.encode()).hexdigest())
        self.guard.start();self.addCleanup(self.guard.stop)
    def factory(self,host,**kwargs):
        self.assertEqual(host,'api.notion.com');self.assertEqual(kwargs['port'],443)
        self.assertTrue(kwargs['context'].check_hostname)
        owner=self
        class Connection:
            def request(self,method,path,headers):owner.calls.append((method,path))
            def getresponse(self):
                class Response:
                    status=owner.status
                    def getheader(self,*args):return 'application/json'
                    def read(self,size):return (owner.raw if owner.raw is not None else json.dumps(owner.page).encode())[:size]
                return Response()
            def close(self):owner.closed=True
        return Connection()
    def test_exact_root_single_get_and_no_private_output(self):
        result=probe.probe(self.root,'synthetic-secret',self.factory)
        self.assertEqual(self.calls,[('GET','/v1/pages/'+self.root)])
        self.assertEqual(result['writes'],0);self.assertTrue(self.closed)
        self.assertNotIn(self.root,json.dumps(result));self.assertNotIn('synthetic-secret',json.dumps(result))
    def test_wrong_binding_or_invalid_secret_denied_before_network(self):
        for root,token in [('2'*32,'secret'),(self.root,''),(self.root,'secret\r\nheader')]:
            with self.assertRaises(Exception):probe.probe(root,token,self.factory)
        self.assertEqual(self.calls,[])
    def test_redirect_and_errors_close_without_retry(self):
        for status in (302,401,403,404,429,500):
            self.calls=[];self.status=status
            with self.assertRaises(probe.ProbeHold):probe.probe(self.root,'secret',self.factory)
            self.assertEqual(len(self.calls),1);self.assertTrue(self.closed)
    def test_identity_title_and_archived_mismatch_hold(self):
        for key,value in [('id','2'*32),('archived',True),('properties',{})]:
            old=self.page[key];self.page[key]=value
            with self.assertRaises(Exception):probe.probe(self.root,'secret',self.factory)
            self.page[key]=old
    def test_oversized_malformed_and_duplicate_json_hold(self):
        for raw in (b'x'*(probe.MAX_BYTES+1),b'invalid',b'{"id":1,"id":2}'):
            self.raw=raw
            with self.assertRaises(Exception):probe.probe(self.root,'secret',self.factory)
            self.assertTrue(self.closed)
    def test_disabled_main_and_redacted_failure(self):
        with patch.dict(probe.os.environ,{},clear=True),patch('sys.stdout',new_callable=io.StringIO) as out:
            self.assertEqual(probe.main(),2);self.assertIn('SKIPPED',out.getvalue())
        with patch.dict(probe.os.environ,{'NOTION_READ_PROBE_CONFIRMED':'true'},clear=True),patch('sys.stdout',new_callable=io.StringIO) as out:
            self.assertEqual(probe.main(),2);self.assertIn('BLOCKED',out.getvalue())
