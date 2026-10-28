import importlib.util
import json
import io
import os
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import unittest

spec=importlib.util.spec_from_file_location('content',Path(__file__).resolve().parents[2]/'tools/notion_audit_content_probe.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ContentTests(unittest.TestCase):
    def output_for(self,error):
        output=io.StringIO()
        with patch.dict(os.environ,{'NOTION_AUDIT_READ_CONFIRMED':'true',
                'NOTION_AUDIT_CONTENT_CONFIRMED':'true','NOTION_SANDBOX_TOKEN':'secret-sentinel'}), \
                patch.object(m,'probe',side_effect=error),redirect_stdout(output):
            self.assertEqual(m.main(),2)
        self.assertNotIn('secret-sentinel',output.getvalue())
        return json.loads(output.getvalue())
    def test_known_unsupported_block_reports_only_schema_label_and_still_holds(self):
        with self.assertRaises(m.Unsupported) as caught:
            self.invoke([dict(object='list',results=[self.block(type='table',
                table={'private':'body-sentinel'})],has_more=False)])
        result=self.output_for(caught.exception)
        self.assertEqual(result,dict(result='BLOCKED',reason='CONTENT_UNSUPPORTED_TYPE',
            unsupported_category='BLOCK_TYPE',unsupported_type='table'))
        self.assertTrue(all(call[0]=='GET' for call in self.calls));self.assertEqual(self.closed,1)
    def test_known_unsupported_mention_reports_only_schema_label(self):
        block=self.block(paragraph={'rich_text':[{'type':'mention','plain_text':'body-sentinel',
            'mention':{'type':'link_preview','link_preview':{'url':'private-sentinel'}}}]})
        with self.assertRaises(m.Unsupported) as caught:
            self.invoke([dict(object='list',results=[block],has_more=False)])
        self.assertEqual(self.output_for(caught.exception),dict(result='BLOCKED',
            reason='CONTENT_UNSUPPORTED_TYPE',unsupported_category='MENTION_TYPE',
            unsupported_type='link_preview'))
    def test_unknown_provider_types_and_mutated_diagnostics_never_echo(self):
        for category in ('BLOCK_TYPE','MENTION_TYPE'):
            for value in ('private-sentinel\nsecret-sentinel',{'private':'sentinel'},['private']):
                result=self.output_for(m.Unsupported(category,value))
                self.assertEqual(result['unsupported_type'],'OTHER')
                self.assertNotIn('sentinel',json.dumps(result))
        error=m.Unsupported('BLOCK_TYPE','table')
        error.category=['private-sentinel'];error.label='private-sentinel'
        self.assertEqual(self.output_for(error)['unsupported_category'],'OTHER')
    def test_other_failures_have_no_diagnostics(self):
        self.assertEqual(self.output_for(m.read.Hold('CONTENT_MALFORMED')),
            dict(result='BLOCKED',reason='CONTENT_MALFORMED'))
    def block(self,n=1,**changes):
        b=dict(object='block',id=f'{n:032x}',type='paragraph',paragraph={'rich_text':[]},has_children=False,
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
    def test_unknown_type_and_malformed_rich_text_hold(self):
        for block in (self.block(type='invented',invented={}),self.block(paragraph={}),
                      self.block(paragraph={'rich_text':'invalid'}),
                      self.block(paragraph={'rich_text':[{'type':'text','plain_text':'x','text':{'content':'y'}}]})):
            with self.assertRaises(m.read.Hold):self.invoke([dict(object='list',results=[block],has_more=False)])
    def test_unsupported_and_malformed_mentions_hold(self):
        for mention in ({'type':'invented','invented':None},{'type':'page','page':None},
                        {'type':'page','page':{'id':'invalid'}},{'type':'date','date':{'start':'invalid'}}):
            block=self.block(paragraph={'rich_text':[{'type':'mention','plain_text':'x','mention':mention}]})
            with self.assertRaises(m.read.Hold):self.invoke([dict(object='list',results=[block],has_more=False)])
    def test_supported_page_and_date_mentions_are_observed(self):
        for mention in ({'type':'page','page':{'id':m.read.AUDIT_ID}},
                        {'type':'date','date':{'start':'2026-10-28','end':None,'time_zone':None}}):
            block=self.block(paragraph={'rich_text':[{'type':'mention','plain_text':'x','mention':mention}]})
            result=self.invoke([dict(object='list',results=[block],has_more=False)])
            self.assertEqual(result['blocks_observed'],1)
