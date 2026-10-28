"""Opt-in bounded top-level content GETs. No body, token or text is logged."""
import importlib.util
import json
import os
from pathlib import Path
import time
from urllib.parse import urlencode
from uuid import UUID

spec=importlib.util.spec_from_file_location('audit_read',Path(__file__).with_name('notion_audit_access_probe.py'))
read=importlib.util.module_from_spec(spec);spec.loader.exec_module(read)

RICH_TYPES={'paragraph','heading_1','heading_2','heading_3','bulleted_list_item',
            'numbered_list_item','quote','callout','to_do','toggle','code'}


def validate_payload(block):
    kind=block['type'];payload=block[kind]
    if kind in RICH_TYPES:
        rich=payload.get('rich_text')
        if type(rich) is not list:raise read.Hold('CONTENT_MALFORMED')
        for part in rich:
            if (type(part) is not dict or part.get('type') not in {'text','mention','equation'}
                    or type(part.get('plain_text')) is not str
                    or type(part.get(part['type'])) is not dict):raise read.Hold('CONTENT_MALFORMED')
            value=part[part['type']]
            if part['type']=='text' and (type(value.get('content')) is not str
                    or value['content']!=part['plain_text']):raise read.Hold('CONTENT_MALFORMED')
            if part['type']=='equation' and type(value.get('expression')) is not str:
                raise read.Hold('CONTENT_MALFORMED')
            if part['type']=='mention' and (type(value.get('type')) is not str
                    or value['type'] not in value):raise read.Hold('CONTENT_MALFORMED')
        if kind=='code' and (type(payload.get('language')) is not str or not payload['language']):
            raise read.Hold('CONTENT_MALFORMED')
        if kind=='to_do' and type(payload.get('checked')) is not bool:raise read.Hold('CONTENT_MALFORMED')
    elif kind=='divider':
        if payload!={}:raise read.Hold('CONTENT_MALFORMED')
    elif kind=='child_page':
        if type(payload.get('title')) is not str:raise read.Hold('CONTENT_MALFORMED')
    else:raise read.Hold('CONTENT_UNSUPPORTED_TYPE')


def probe(token,factory=None,pause=time.sleep):
    read.probe(token,factory)  # Exact identity/inactive status checked first.
    cursors=set();blocks=set();cursor=None;requests=1
    for _ in range(10):
        pause(0.4)
        query={'page_size':100}
        if cursor is not None:query['start_cursor']=cursor
        conn=(factory or read.http.client.HTTPSConnection)('api.notion.com',port=443,timeout=10,context=read.ssl.create_default_context())
        try:
            conn.request('GET','/v1/blocks/'+read.AUDIT_ID+'/children?'+urlencode(query),headers={
                'Authorization':'Bearer '+token,'Notion-Version':'2022-06-28','Accept':'application/json'})
            requests+=1;response=conn.getresponse()
            if response.status!=200:raise read.Hold('CONTENT_HTTP_NOT_OK')
            if response.getheader('Content-Type','').split(';')[0].strip()!='application/json':
                raise read.Hold('CONTENT_MALFORMED')
            raw=response.read(read.MAX_BYTES+1)
            if len(raw)>read.MAX_BYTES:raise read.Hold('CONTENT_OVERSIZED')
            page=json.loads(raw,object_pairs_hook=read.unique)
            if (type(page) is not dict or page.get('object')!='list'
                    or type(page.get('results')) is not list or len(page['results'])>100
                    or type(page.get('has_more')) is not bool):raise read.Hold('CONTENT_MALFORMED')
            for block in page['results']:
                if (type(block) is not dict or block.get('object')!='block'
                        or type(block.get('has_children')) is not bool
                        or block.get('archived') is not False or block.get('in_trash',False) is not False
                        or type(block.get('type')) is not str or block['type']=='unsupported'
                        or type(block.get(block['type'])) is not dict):raise read.Hold('CONTENT_MALFORMED')
                validate_payload(block)
                parent=block.get('parent')
                if (type(parent) is not dict or parent.get('type')!='page_id'
                        or UUID(parent['page_id']).hex!=read.AUDIT_ID):raise read.Hold('CONTENT_PARENT_MISMATCH')
                identity=UUID(block['id']).hex
                if identity in blocks:raise read.Hold('CONTENT_DUPLICATE')
                blocks.add(identity)
                if block['has_children']:raise read.Hold('CONTENT_NESTED_UNVERIFIED')
            if not page['has_more']:
                if page.get('next_cursor') is not None:raise read.Hold('CONTENT_MALFORMED')
                return dict(operation='READ_ONLY',requests=requests,writes=0,audit_identity='MATCHED',
                            content_read='COMPLETE_BOUNDED_TOP_LEVEL',blocks_observed=len(blocks),
                            nested_content='NONE_OBSERVED',atomic_snapshot='NOT_PROVEN',
                            bridge_execution='NOT_TESTED',write_capability='NOT_TESTED')
            cursor=page.get('next_cursor')
            if type(cursor) is not str or not cursor or len(cursor)>4096 or cursor in cursors:
                raise read.Hold('CONTENT_CURSOR_INVALID')
            cursors.add(cursor)
        finally:conn.close()
    raise read.Hold('CONTENT_PAGINATION_LIMIT')


def main():
    if (os.environ.get('NOTION_AUDIT_READ_CONFIRMED')!='true'
            or os.environ.get('NOTION_AUDIT_CONTENT_CONFIRMED')!='true'):
        print('{"result":"SKIPPED"}');return 2
    try:result=probe(os.environ.pop('NOTION_SANDBOX_TOKEN',''))
    except read.Hold as error:
        codes={'CONTENT_HTTP_NOT_OK','CONTENT_MALFORMED','CONTENT_OVERSIZED','CONTENT_PARENT_MISMATCH',
               'CONTENT_DUPLICATE','CONTENT_NESTED_UNVERIFIED','CONTENT_CURSOR_INVALID','CONTENT_PAGINATION_LIMIT',
               'CONTENT_UNSUPPORTED_TYPE'}
        print(json.dumps(dict(result='BLOCKED',reason=str(error) if str(error) in codes else 'CONTENT_UNAVAILABLE')));return 2
    except Exception:
        print('{"result":"BLOCKED","reason":"CONTENT_UNAVAILABLE"}');return 2
    print(json.dumps(result,sort_keys=True));return 0


if __name__=='__main__':raise SystemExit(main())
