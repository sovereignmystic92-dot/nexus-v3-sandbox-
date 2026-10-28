import importlib.util
import json
from pathlib import Path
from unittest.mock import patch
import unittest

spec=importlib.util.spec_from_file_location('content',Path(__file__).resolve().parents[2]/'tools/notion_audit_content_probe.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ContentTests(unittest.TestCase):
    def block(self,n=1,**changes):
        b=dict(object='block',id=f'{n:032x}',type='paragraph',paragraph={},has_children=False,
               archived=False,in_trash=False,parent=dict(type='page_id',page_id=m.read.AUDIT_ID));b.update(changes);return b
    def invoke(self,pages):
        self.calls=[];self.closed=0;owner=self
        class Connection:
            def request(self,*args,**kwargs):owner.calls.append(args)
            def getresponse(self):
                body=pages[min(len(owner.calls)-1,len(pages)-1)]
                class Response:
                    status=200
                    def getheader(self,*_):return 'application/json'
                    def read(self,n):return json.dumps(body).encode()[:n]
                return Response()
            def close(self):owner.closed+=1
        with patch.object(m.read,'probe',return_value={}):
            return m.probe('synthetic-token',lambda *_,**__:Connection(),pause=lambda _:None)
    def test_complete_pagination_uses_only_get_and_closes(self):
        result=self.invoke([dict(object='list',results=[self.block()],has_more=True,next_cursor='next'),
                            dict(object='list',results=[self.block(2)],has_more=False,next_cursor=None)])
        self.assertEqual(result['blocks_observed'],2);self.assertEqual(result['writes'],0)
        self.assertTrue(all(x[0]=='GET' for x in self.calls));self.assertEqual(self.closed,2)
    def test_nested_duplicate_wrong_parent_and_unsupported_hold(self):
        for blocks in ([self.block(has_children=True)],[self.block(),self.block()],
                       [self.block(parent=dict(type='page_id',page_id='00000000000000000000000000000002'))],
                       [self.block(type='unsupported',unsupported={})]):
            with self.assertRaises(m.read.Hold):self.invoke([dict(object='list',results=blocks,has_more=False)])
    def test_repeated_missing_cursor_and_pagination_limit_hold(self):
        for cursor in (None,'same'):
            with self.assertRaises(m.read.Hold):self.invoke([dict(object='list',results=[],has_more=True,next_cursor=cursor)])
    def test_truthy_has_more_and_missing_children_hold(self):
        for p in (dict(object='list',results=[],has_more=1),
                  dict(object='list',results=[dict(self.block(),has_children=None)],has_more=False)):
            with self.assertRaises(m.read.Hold):self.invoke([p])
    def test_ten_page_limit_holds_without_retry(self):
        pages=[dict(object='list',results=[],has_more=True,next_cursor=str(i)) for i in range(10)]
        with self.assertRaises(m.read.Hold):self.invoke(pages)
        self.assertEqual(len(self.calls),10);self.assertEqual(self.closed,10)
