"""Bounded Notion REST shape adapter; no credential lookup or live execution.

Host request(method,path,payload) supplies authenticated decoded API responses.
It must pin api.notion.com, API version, timeouts, and never retry PATCH blindly.
Only explicit write_enabled=True permits one checkpoint-code-block append.
"""
import json
import re
from urllib.parse import urlencode
from uuid import UUID
import urllib.request


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Redirect refused')


class NotionRequest:
    """Pinned HTTPS client; token supplied by authorized host, never discovered.

    No automatic retries, redirects, credential logging or environment reads.
    HTTP failures are sanitized and remain uncertain for writes.
    """
    def __init__(self,page_id,token,api_version,*,write_enabled=False):
        self.page_id=UUID(page_id).hex
        if (type(token) is not str or not token or '\n' in token or '\r' in token
                or type(api_version) is not str or re.fullmatch(r'\d{4}-\d{2}-\d{2}',api_version) is None
                or type(write_enabled) is not bool):
            raise ValueError('Explicit authenticated configuration required')
        self._token,self.version,self.write_enabled=token,api_version,write_enabled
        self._opener=urllib.request.build_opener(_NoRedirect())
    def __call__(self,method,path,payload):
        page='/v1/pages/'+self.page_id
        children='/v1/blocks/'+self.page_id+'/children'
        if method=='GET':
            if path!=page and not path.startswith(children+'?'):
                raise ValueError('Unbound API path')
            if payload is not None:raise ValueError('GET payload refused')
        elif method=='PATCH':
            if not self.write_enabled or path!=children:
                raise ValueError('Unbound or disabled write')
        else:raise ValueError('Method refused')
        data=None if payload is None else json.dumps(payload,allow_nan=False).encode('utf-8')
        request=urllib.request.Request('https://api.notion.com'+path,data=data,method=method,
            headers={'Authorization':'Bearer '+self._token,'Notion-Version':self.version,
                     'Content-Type':'application/json'})
        try:
            with self._opener.open(request,timeout=30) as response:
                raw=response.read(2*1024*1024+1)
                if len(raw)>2*1024*1024:raise ValueError('Response limit')
                value=json.loads(raw)
                if type(value) is not dict or value.get('object')=='error':raise ValueError('API error')
                return value
        except Exception:
            raise RuntimeError('Notion request unavailable; reconcile uncertain writes') from None


class NotionCheckpointAPI:
    def __init__(self,page_id,request,*,write_enabled=False,max_pages=10):
        self.page_id=UUID(page_id).hex
        if type(write_enabled) is not bool or type(max_pages) is not int or not 1<=max_pages<=100:
            raise ValueError('Explicit bounded configuration required')
        self.request,self.write_enabled,self.max_pages=request,write_enabled,max_pages
    def _bound(self,page_id):
        if UUID(page_id).hex!=self.page_id:raise ValueError('Unbound destination')
    def fetch_page(self,page_id):
        self._bound(page_id)
        page=self.request('GET','/v1/pages/'+self.page_id,None)
        if (type(page) is not dict or page.get('object')!='page'
                or UUID(page['id']).hex!=self.page_id
                or page.get('archived') is not False or page.get('in_trash') is not False):
            raise ValueError('Unavailable or inactive bound page')
        cursor=None;seen_cursors=set();seen_blocks=set();blocks=[]
        for _ in range(self.max_pages):
            query={'page_size':100}
            if cursor is not None:query['start_cursor']=cursor
            response=self.request('GET','/v1/blocks/'+self.page_id+'/children?'+urlencode(query),None)
            if (type(response) is not dict or response.get('object')!='list'
                    or type(response.get('results')) is not list
                    or type(response.get('has_more')) is not bool):
                raise ValueError('Malformed block inventory')
            for block in response['results']:
                if (type(block) is not dict or block.get('object')!='block'
                        or type(block.get('has_children')) is not bool or block['has_children']
                        or block.get('archived') is not False or block.get('in_trash') is not False):
                    raise ValueError('Nested or unavailable block; complete inventory not proven')
                identity=UUID(block['id']).hex
                if identity in seen_blocks:raise ValueError('Duplicate block inventory')
                seen_blocks.add(identity)
                if block.get('type')=='code':
                    code=block['code']
                    if type(code) is not dict or code.get('language')!='json':
                        continue
                    if type(code.get('rich_text')) is not list:
                        raise ValueError('Malformed JSON code block')
                    parts=[]
                    for rich in code['rich_text']:
                        if (type(rich) is not dict or rich.get('type')!='text'
                                or type(rich.get('plain_text')) is not str):
                            raise ValueError('Nonliteral checkpoint text')
                        parts.append(rich['plain_text'])
                    value=''.join(parts)
                    if '\n```' in value:raise ValueError('Ambiguous code fence in checkpoint')
                    blocks.append('```json\n'+value+'\n```\n')
            if not response['has_more']:
                if response.get('next_cursor') is not None:raise ValueError('Inconsistent pagination')
                return dict(id=self.page_id,metadata={'type':'page'},text=''.join(blocks),
                            truncated=False,unknown_block_count=0,unknown_block_ids=[])
            cursor=response.get('next_cursor')
            if type(cursor) is not str or not cursor or cursor in seen_cursors:
                raise ValueError('Missing or repeated cursor')
            seen_cursors.add(cursor)
        raise ValueError('Pagination bound reached; no complete observation')
    def append_text(self,page_id,text):
        self._bound(page_id)
        if not self.write_enabled:raise ValueError('Live append disabled')
        match=re.fullmatch(r'\n```json\n([^\n]+)\n```\n',text)
        if match is None:raise ValueError('One generated canonical checkpoint block required')
        value=match[1]
        event=json.loads(value)
        if (type(event) is not dict or event.get('event_type')!='NXS_CHECKPOINT_V1'
                or event.get('page_id')!=self.page_id):
            raise ValueError('Only bound checkpoint events permitted')
        chunks=[value[i:i+2000] for i in range(0,len(value),2000)]
        if not chunks or len(chunks)>100:raise ValueError('Checkpoint exceeds append bound')
        payload={'children':[{'object':'block','type':'code','code':{'language':'json',
                    'rich_text':[{'type':'text','text':{'content':s}} for s in chunks]}}]}
        # Exactly one attempt. The higher-level transport must freshly observe.
        return self.request('PATCH','/v1/blocks/'+self.page_id+'/children',payload)
