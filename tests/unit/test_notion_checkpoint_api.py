import json
import unittest
from unittest.mock import patch
from nexus_sandbox.notion_checkpoint_api import NotionCheckpointAPI
from nexus_sandbox.notion_checkpoint_api import NotionRequest

PAGE='00000000000000000000000000000001'


class APITests(unittest.TestCase):
    def test_client_does_not_discover_environment_proxies(self):
        with patch('urllib.request.getproxies',return_value={'https':'http://synthetic.invalid:8080'}) as lookup:
            client=NotionRequest(PAGE,'synthetic-token','2022-06-28')
        lookup.assert_not_called()
        self.assertFalse(any(getattr(handler,'proxies',{}) for handler in client._opener.handlers))
    def test_wrong_missing_or_malformed_parent_never_claims_complete(self):
        for parent in (None,{},dict(type='page_id',page_id='00000000000000000000000000000003'),
                       dict(type='block_id',block_id=PAGE),dict(type='page_id',page_id='invalid')):
            def request(method,path,payload):
                if path.startswith('/v1/pages/'):return self.request(method,path,payload)
                return dict(object='list',results=[dict(self.block(2),parent=parent)],has_more=False,next_cursor=None)
            with self.assertRaises(ValueError):NotionCheckpointAPI(PAGE,request).fetch_page(PAGE)
    def test_missing_or_contradictory_literal_text_never_claims_complete(self):
        for literal in (None,{},dict(content='different'),dict(content=1)):
            block=self.block(2);block['code']['rich_text'][0]['text']=literal
            def request(method,path,payload):
                if path.startswith('/v1/pages/'):return self.request(method,path,payload)
                return dict(object='list',results=[block],has_more=False,next_cursor=None)
            with self.assertRaises(ValueError):NotionCheckpointAPI(PAGE,request).fetch_page(PAGE)
    def test_malformed_code_metadata_never_claims_complete(self):
        for code in (None,{},dict(language=None),dict(language='')):
            def request(method,path,payload):
                if path.startswith('/v1/pages/'):return self.request(method,path,payload)
                return dict(object='list',results=[dict(self.block(2),code=code)],has_more=False,next_cursor=None)
            with self.assertRaises(ValueError):NotionCheckpointAPI(PAGE,request).fetch_page(PAGE)
    def test_pinned_client_refuses_unbound_paths_and_writes(self):
        client=NotionRequest(PAGE,'synthetic-token','2022-06-28')
        for method,path in [('POST','/v1/pages'),('GET','https://other.example/'),
                            ('PATCH','/v1/blocks/'+PAGE+'/children')]:
            with self.assertRaises(ValueError):client(method,path,None)
    def test_client_sanitizes_transport_failure_without_retry(self):
        client=NotionRequest(PAGE,'synthetic-secret','2022-06-28')
        class Failed:
            count=0
            def open(self,*args,**kwargs):
                self.count+=1;raise TimeoutError('synthetic-secret')
        client._opener=Failed()
        with self.assertRaises(RuntimeError) as error:client('GET','/v1/pages/'+PAGE,None)
        self.assertNotIn('synthetic-secret',str(error.exception))
        self.assertEqual(client._opener.count,1)
    def setUp(self):self.calls=[]
    def block(self,n,text='{}'):
        return dict(object='block',id=f'{n:032x}',has_children=False,archived=False,in_trash=False,
                    parent=dict(type='page_id',page_id=PAGE),
                    type='code',code=dict(language='json',rich_text=[dict(type='text',plain_text=text,text=dict(content=text))]))
    def request(self,method,path,payload):
        self.calls.append((method,path,payload))
        if path.startswith('/v1/pages/'):
            return dict(object='page',id=PAGE,archived=False,in_trash=False)
        return dict(object='list',results=[self.block(2)],has_more=False,next_cursor=None)
    def test_fetch_bound_page_and_literal_json(self):
        page=NotionCheckpointAPI(PAGE,self.request).fetch_page(PAGE)
        self.assertEqual(page['text'],'```json\n{}\n```\n')
        self.assertFalse(page['truncated'])
    def test_wrong_destination_and_default_write_make_no_calls(self):
        api=NotionCheckpointAPI(PAGE,self.request)
        with self.assertRaises(ValueError):api.fetch_page('00000000000000000000000000000003')
        with self.assertRaises(ValueError):api.append_text(PAGE,'x')
        self.assertEqual(self.calls,[])
    def test_paginated_inventory_and_repeated_cursor_hold(self):
        def request(method,path,payload):
            if path.startswith('/v1/pages/'):return self.request(method,path,payload)
            if 'start_cursor' not in path:
                return dict(object='list',results=[self.block(2)],has_more=True,next_cursor='next')
            return dict(object='list',results=[self.block(3)],has_more=False,next_cursor=None)
        self.assertEqual(NotionCheckpointAPI(PAGE,request).fetch_page(PAGE)['text'].count('```json'),2)
        with self.assertRaises(ValueError):NotionCheckpointAPI(PAGE,request,max_pages=1).fetch_page(PAGE)
    def test_nested_duplicate_and_malformed_pagination_hold(self):
        for response in (dict(object='list',results=[dict(self.block(2),has_children=True)],has_more=False),
                         dict(object='list',results=[self.block(2),self.block(2)],has_more=False),
                         dict(object='list',results=[],has_more=1)):
            def request(method,path,payload):
                return self.request(method,path,payload) if path.startswith('/v1/pages/') else response
            with self.assertRaises(ValueError):NotionCheckpointAPI(PAGE,request).fetch_page(PAGE)
    def test_append_chunks_once_and_propagates_lost_ack(self):
        value=json.dumps(dict(event_type='NXS_CHECKPOINT_V1',page_id=PAGE,padding='a'*4000),separators=(',',':'))
        def lost(method,path,payload):
            self.calls.append((method,path,payload));raise TimeoutError()
        api=NotionCheckpointAPI(PAGE,lost,write_enabled=True)
        with self.assertRaises(TimeoutError):api.append_text(PAGE,'\n```json\n'+value+'\n```\n')
        self.assertEqual(len(self.calls),1)
        parts=self.calls[0][2]['children'][0]['code']['rich_text']
        self.assertEqual(''.join(p['text']['content'] for p in parts),value)
        self.assertTrue(all(len(p['text']['content'])<=2000 for p in parts))
