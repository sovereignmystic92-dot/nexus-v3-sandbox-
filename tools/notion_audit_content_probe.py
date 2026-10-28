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

shared_path=Path(__file__).with_name('notion_inventory.py')
if not shared_path.is_file():
    shared_path=Path(__file__).resolve().parents[1]/'src/nexus_sandbox/notion_inventory.py'
shared_spec=importlib.util.spec_from_file_location('inventory',shared_path)
inventory=importlib.util.module_from_spec(shared_spec);shared_spec.loader.exec_module(inventory)
Unsupported=inventory.Unsupported
unsupported_report=inventory.unsupported_report
validate_payload=inventory.validate_payload


def probe(token,factory=None,pause=time.sleep):
    read.probe(token,factory)
    def fetch_children(parent_id,query):
        pause(0.4)
        conn=(factory or read.http.client.HTTPSConnection)('api.notion.com',port=443,timeout=10,context=read.ssl.create_default_context())
        try:
            conn.request('GET','/v1/blocks/'+parent_id+'/children?'+urlencode(query),headers={
                'Authorization':'Bearer '+token,'Notion-Version':'2022-06-28','Accept':'application/json'})
            response=conn.getresponse()
            if response.status!=200:raise read.Hold('CONTENT_HTTP_NOT_OK')
            if response.getheader('Content-Type','').split(';')[0].strip()!='application/json':
                raise read.Hold('CONTENT_MALFORMED')
            raw=response.read(read.MAX_BYTES+1)
            if len(raw)>read.MAX_BYTES:raise read.Hold('CONTENT_OVERSIZED')
            return json.loads(raw,object_pairs_hook=inventory.unique_pairs)
        finally:conn.close()
    _,report=inventory.observe(read.AUDIT_ID,fetch_children)
    return report


def main():
    if (os.environ.get('NOTION_AUDIT_READ_CONFIRMED')!='true'
            or os.environ.get('NOTION_AUDIT_CONTENT_CONFIRMED')!='true'):
        print('{"result":"SKIPPED"}');return 2
    try:result=probe(os.environ.pop('NOTION_SANDBOX_TOKEN',''))
    except (read.Hold,inventory.InventoryError) as error:
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
