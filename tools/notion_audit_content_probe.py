"""Opt-in bounded top-level and table-row GETs. No body, token or text is logged."""
import importlib.util
import json
import os
from pathlib import Path
import time
from datetime import datetime
from urllib.parse import urlencode
from uuid import UUID

spec=importlib.util.spec_from_file_location('audit_read',Path(__file__).with_name('notion_audit_access_probe.py'))
read=importlib.util.module_from_spec(spec);spec.loader.exec_module(read)

RICH_TYPES={'paragraph','heading_1','heading_2','heading_3','bulleted_list_item',
            'numbered_list_item','quote','callout','to_do','toggle','code'}

# Only fixed schema labels may leave the process. Never log provider strings.
DIAGNOSTIC_TYPES={
    'BLOCK_TYPE':frozenset({'bookmark','breadcrumb','child_database','column','column_list',
        'embed','equation','file','image','link_preview','link_to_page','pdf','synced_block',
        'table','table_of_contents','table_row','template','video','audio'}),
    'MENTION_TYPE':frozenset({'link_preview','template_mention','custom_emoji'})}


class Unsupported(read.Hold):
    def __init__(self,category,value):
        super().__init__('CONTENT_UNSUPPORTED_TYPE')
        self.category=category if category in DIAGNOSTIC_TYPES else 'OTHER'
        allowed=DIAGNOSTIC_TYPES.get(self.category,frozenset())
        self.label=value if type(value) is str and value in allowed else 'OTHER'


def unsupported_report(error):
    # Revalidate at the output boundary, including mutated exception attributes.
    category=getattr(error,'category',None);label=getattr(error,'label',None)
    if type(category) is not str or category not in DIAGNOSTIC_TYPES:category='OTHER'
    allowed=DIAGNOSTIC_TYPES.get(category,frozenset())
    if type(label) is not str or label not in allowed:label='OTHER'
    return dict(unsupported_category=category,unsupported_type=label)


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
            if part['type']=='mention':
                subtype=value.get('type')
                if subtype not in {'page','database','data_source','user','date'}:
                    raise Unsupported('MENTION_TYPE',subtype)
                target=value.get(subtype)
                if type(target) is not dict:raise read.Hold('CONTENT_MALFORMED')
                try:
                    if subtype=='date':
                        if type(target.get('start')) is not str:raise ValueError()
                        datetime.fromisoformat(target['start'])
                        if target.get('end') is not None:
                            if type(target['end']) is not str:raise ValueError()
                            datetime.fromisoformat(target['end'])
                        if target.get('time_zone') is not None and type(target['time_zone']) is not str:
                            raise ValueError()
                    else:
                        if type(target.get('id')) is not str:raise ValueError()
                        UUID(target['id'])
                except (ValueError,TypeError,AttributeError):raise read.Hold('CONTENT_MALFORMED') from None
        if kind=='code' and (type(payload.get('language')) is not str or not payload['language']):
            raise read.Hold('CONTENT_MALFORMED')
        if kind=='to_do' and type(payload.get('checked')) is not bool:raise read.Hold('CONTENT_MALFORMED')
    elif kind=='divider':
        if payload!={}:raise read.Hold('CONTENT_MALFORMED')
    elif kind=='child_page':
        if type(payload.get('title')) is not str:raise read.Hold('CONTENT_MALFORMED')
    else:raise Unsupported('BLOCK_TYPE',kind)


def probe(token,factory=None,pause=time.sleep):
    read.probe(token,factory)
    blocks=set();requests=1;tables=0;rows=0

    def children(parent_id,parent_type):
        nonlocal requests
        cursors=set();cursor=None
        while True:
            if requests>=11:raise read.Hold('CONTENT_PAGINATION_LIMIT')
            pause(0.4)
            query={'page_size':100}
            if cursor is not None:query['start_cursor']=cursor
            conn=(factory or read.http.client.HTTPSConnection)('api.notion.com',port=443,timeout=10,context=read.ssl.create_default_context())
            try:
                conn.request('GET','/v1/blocks/'+parent_id+'/children?'+urlencode(query),headers={
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
            finally:conn.close()
            # Validate the entire page before exposing any child as a read target.
            validated=[]
            for block in page['results']:
                if (type(block) is not dict or block.get('object')!='block'
                        or type(block.get('has_children')) is not bool
                        or block.get('archived') is not False or block.get('in_trash',False) is not False
                        or type(block.get('type')) is not str or block['type']=='unsupported'
                        or type(block.get(block['type'])) is not dict):raise read.Hold('CONTENT_MALFORMED')
                parent=block.get('parent')
                try:
                    if (type(parent) is not dict or parent.get('type')!=parent_type
                            or UUID(parent[parent_type]).hex!=parent_id):
                        raise read.Hold('CONTENT_PARENT_MISMATCH')
                    identity=UUID(block['id']).hex
                except (ValueError,TypeError,KeyError,AttributeError):
                    raise read.Hold('CONTENT_PARENT_MISMATCH') from None
                if identity in blocks:raise read.Hold('CONTENT_DUPLICATE')
                blocks.add(identity);validated.append((block,identity))
            more=page['has_more'];next_cursor=page.get('next_cursor')
            if more:
                if (type(next_cursor) is not str or not next_cursor or len(next_cursor)>4096
                        or next_cursor in cursors):raise read.Hold('CONTENT_CURSOR_INVALID')
                cursors.add(next_cursor)
            elif next_cursor is not None:raise read.Hold('CONTENT_MALFORMED')
            yield from validated
            if not more:return
            cursor=next_cursor

    for block,identity in children(read.AUDIT_ID,'page_id'):
        if block['type']=='table':
            payload=block['table'];width=payload.get('table_width')
            if (type(width) is not int or not 1<=width<=100
                    or type(payload.get('has_column_header')) is not bool
                    or type(payload.get('has_row_header')) is not bool
                    or not block['has_children']):raise read.Hold('CONTENT_MALFORMED')
            table_rows=0
            for row,_ in children(identity,'block_id'):
                if row['type']!='table_row':raise read.Hold('CONTENT_MALFORMED')
                if row['has_children']:raise read.Hold('CONTENT_NESTED_UNVERIFIED')
                cells=row['table_row'].get('cells')
                if type(cells) is not list or len(cells)!=width:raise read.Hold('CONTENT_MALFORMED')
                for cell in cells:
                    validate_payload({'type':'paragraph','paragraph':{'rich_text':cell}})
                table_rows+=1;rows+=1
            if not table_rows:raise read.Hold('CONTENT_MALFORMED')
            tables+=1
        else:
            # A row outside its enrolled table is never accepted.
            validate_payload(block)
            if block['has_children']:raise read.Hold('CONTENT_NESTED_UNVERIFIED')
    return dict(operation='READ_ONLY',requests=requests,writes=0,audit_identity='MATCHED',
                content_read='COMPLETE_BOUNDED_TOP_LEVEL_AND_TABLE_ROWS',blocks_observed=len(blocks),
                tables_observed=tables,table_rows_observed=rows,
                nested_content='TABLE_ROWS_ONLY' if tables else 'NONE_OBSERVED',
                atomic_snapshot='NOT_PROVEN',bridge_execution='NOT_TESTED',write_capability='NOT_TESTED')


def main():
    if (os.environ.get('NOTION_AUDIT_READ_CONFIRMED')!='true'
            or os.environ.get('NOTION_AUDIT_CONTENT_CONFIRMED')!='true'):
        print('{"result":"SKIPPED"}');return 2
    try:result=probe(os.environ.pop('NOTION_SANDBOX_TOKEN',''))
    except read.Hold as error:
        codes={'CONTENT_HTTP_NOT_OK','CONTENT_MALFORMED','CONTENT_OVERSIZED','CONTENT_PARENT_MISMATCH',
               'CONTENT_DUPLICATE','CONTENT_NESTED_UNVERIFIED','CONTENT_CURSOR_INVALID','CONTENT_PAGINATION_LIMIT',
               'CONTENT_UNSUPPORTED_TYPE'}
        report=dict(result='BLOCKED',reason=str(error) if str(error) in codes else 'CONTENT_UNAVAILABLE')
        if isinstance(error,Unsupported):report.update(unsupported_report(error))
        print(json.dumps(report));return 2
    except Exception:
        print('{"result":"BLOCKED","reason":"CONTENT_UNAVAILABLE"}');return 2
    print(json.dumps(result,sort_keys=True));return 0


if __name__=='__main__':raise SystemExit(main())
