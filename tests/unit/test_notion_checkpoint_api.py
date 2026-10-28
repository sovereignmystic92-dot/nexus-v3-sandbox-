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

    def table(self):
        return dict(object='block',id=f'{10:032x}',type='table',table=dict(table_width=2,
            has_column_header=True,has_row_header=False),has_children=True,archived=False,in_trash=False,
            parent=dict(type='page_id',page_id=PAGE))
    def row(self,n=11):
        return dict(object='block',id=f'{n:032x}',type='table_row',table_row={'cells':[[],[]]},
            has_children=False,archived=False,in_trash=False,parent=dict(type='block_id',block_id=f'{10:032x}'))
    def inventory(self,pages,max_pages=10):
        calls=[]
        def request(method,path,payload):
            calls.append((method,path,payload))
            if path.startswith('/v1/pages/'):return dict(object='page',id=PAGE,archived=False,in_trash=False)
            return pages.pop(0)
        result=NotionCheckpointAPI(PAGE,request,max_pages=max_pages).fetch_page(PAGE)
        return result,calls
    def page(self,blocks,more=False,cursor=None):
        return dict(object='list',results=blocks,has_more=more,next_cursor=cursor)
    def test_table_and_root_pagination_preserve_all_checkpoint_blocks(self):
        page,calls=self.inventory([self.page([self.block(2,'{"first":1}'),self.table()],True,'root'),
            self.page([self.row()],True,'rows'),self.page([self.row(12)]),
            self.page([self.block(3,'{"last":2}')])])
        self.assertIn('{"first":1}',page['text']);self.assertIn('{"last":2}',page['text'])
        self.assertEqual(page['text'].count('```json'),2)
        self.assertEqual(page['inventory']['requests'],5)
        self.assertEqual(page['inventory']['table_rows_observed'],2)
        self.assertTrue(all(method=='GET' for method,_,_ in calls))
    def test_table_bad_rows_and_cross_table_identity_never_claim_complete(self):
        wrong=self.row();wrong['parent']['block_id']=f'{99:032x}'
        bad=self.row();bad['table_row']['cells']=[[]]
        nested=self.row();nested['has_children']=True
        literal=self.row();literal['table_row']['cells'][0]=[dict(type='text',plain_text='a',text={'content':'b'})]
        for rows in ([wrong],[bad],[nested],[literal],[self.row(),self.row()],[]):
            with self.assertRaises(ValueError):self.inventory([self.page([self.table()]),self.page(rows)])
    def test_table_budget_and_incomplete_root_cannot_return_checkpoint(self):
        with self.assertRaises(ValueError):self.inventory([self.page([self.block(2),self.table()])],max_pages=1)
        with self.assertRaises(ValueError):self.inventory([self.page([self.table()]),self.page([self.row()],True,'x')],max_pages=2)
    def test_unknown_root_type_and_orphan_table_row_hold(self):
        unknown=self.block(2);unknown.update(type='invented',invented={})
        orphan=self.row();orphan['parent']=dict(type='page_id',page_id=PAGE)
        for block in (unknown,orphan):
            with self.assertRaises(ValueError):self.inventory([self.page([block])])
    def test_client_reads_only_observed_bound_table_paths(self):
        client=NotionRequest(PAGE,'synthetic-token','2022-06-28')
        rowpath='/v1/blocks/'+f'{10:032x}'+'/children?page_size=100'
        with self.assertRaises(ValueError):client('GET',rowpath,None)
        owner=self
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return json.dumps(owner.page([owner.table()])).encode()
        class Opener:
            def open(self,request,timeout):return Response()
        client._opener=Opener()
        client('GET','/v1/blocks/'+PAGE+'/children?page_size=100',None)
        client('GET',rowpath,None)
        with self.assertRaises(ValueError):client('PATCH',rowpath,None)
        with self.assertRaises(ValueError):client('GET','/v1/blocks/'+f'{99:032x}'+'/children?page_size=100',None)
    def test_client_rejects_table_enrollment_from_other_page(self):
        table=self.table();table['parent']['page_id']=f'{99:032x}'
        from nexus_sandbox.notion_inventory import enrolled_table_id
        with self.assertRaises(ValueError):enrolled_table_id(table,PAGE)
