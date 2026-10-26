import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('notion_boundary_probe',Path(__file__).resolve().parents[2]/'tools/notion_boundary_probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


class NotionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.root='1'*32;self.control='2'*32;self.status=404;self.calls=[];self.closed=False
        self.commit=patch.object(probe,'DENIED_COMMITMENT',hashlib.sha256(self.control.encode()).hexdigest())
        self.commit.start();self.addCleanup(self.commit.stop)
        self.positive=patch.object(probe.read,'probe',return_value={'root_identity':'MATCHED'})
        self.positive_mock=self.positive.start();self.addCleanup(self.positive.stop)
    def factory(self,host,**kwargs):
        self.assertEqual(host,'api.notion.com');self.assertTrue(kwargs['context'].check_hostname)
        owner=self
        class Connection:
            def request(self,method,path,headers):owner.calls.append((method,path))
            def getresponse(self):
                class Response:
                    status=owner.status
                    def read(self,*args):raise AssertionError('Control body must never be read')
                return Response()
            def close(self):owner.closed=True
        return Connection()
    def test_denial_after_positive_read(self):
        result=probe.boundary(self.root,self.control,'secret',self.factory)
        self.positive_mock.assert_called_once()
        self.assertEqual(self.calls,[('GET','/v1/pages/'+self.control)])
        self.assertEqual(result['unshared_control'],'NOT_ACCESSIBLE_404');self.assertTrue(self.closed)
    def test_accessible_control_holds_without_body_read(self):
        self.status=200
        with self.assertRaisesRegex(probe.read.ProbeHold,'CONTROL_ACCESSIBLE'):
            probe.boundary(self.root,self.control,'secret',self.factory)
        self.assertTrue(self.closed)
    def test_other_status_is_inconclusive_and_never_retried(self):
        for status in (301,401,403,429,500):
            self.status=status;self.calls=[]
            with self.assertRaisesRegex(probe.read.ProbeHold,'CONTROL_DENIAL_INCONCLUSIVE'):
                probe.boundary(self.root,self.control,'secret',self.factory)
            self.assertEqual(len(self.calls),1)
    def test_wrong_control_denied_before_positive_read(self):
        with self.assertRaises(probe.read.ProbeHold):probe.boundary(self.root,'3'*32,'secret',self.factory)
        self.positive_mock.assert_not_called();self.assertEqual(self.calls,[])
    def test_failed_positive_prevents_negative_request(self):
        self.positive_mock.side_effect=probe.read.ProbeHold('TOKEN_REJECTED')
        with self.assertRaises(probe.read.ProbeHold):probe.boundary(self.root,self.control,'secret',self.factory)
        self.assertEqual(self.calls,[])
