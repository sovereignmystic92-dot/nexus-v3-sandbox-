"""One explicitly confirmed GET of Foundation Audit metadata; no write method."""
import http.client
import json
import os
import ssl
from uuid import UUID

AUDIT_ID='4018c067daa48122b82ec2ae8067d021'
MAX_BYTES=1024*1024


class Hold(Exception):pass


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise Hold('MALFORMED_RESPONSE')
        result[key]=value
    return result


def probe(token,factory=None):
    if (type(token) is not str or not 0<len(token)<=4096
            or any(not 33<=ord(c)<=126 for c in token)):
        raise Hold('TOKEN_INVALID')
    conn=(factory or http.client.HTTPSConnection)('api.notion.com',port=443,timeout=10,context=ssl.create_default_context())
    try:
        conn.request('GET','/v1/pages/'+AUDIT_ID,headers={
            'Authorization':'Bearer '+token,'Notion-Version':'2022-06-28','Accept':'application/json'})
        response=conn.getresponse()
        if response.status!=200:
            raise Hold({401:'TOKEN_REJECTED',403:'ACCESS_FORBIDDEN',404:'PAGE_UNAVAILABLE',
                        429:'RATE_LIMITED'}.get(response.status,'HTTP_NOT_OK'))
        if response.getheader('Content-Type','').split(';')[0].strip()!='application/json':
            raise Hold('MALFORMED_RESPONSE')
        raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:raise Hold('MALFORMED_RESPONSE')
        page=json.loads(raw,object_pairs_hook=unique)
        if (type(page) is not dict or page.get('object')!='page'
                or UUID(page['id']).hex!=AUDIT_ID or page.get('archived') is not False
                or page.get('in_trash',False) is not False):
            raise Hold('TARGET_NOT_VERIFIED')
        return dict(operation='READ_ONLY',requests=1,writes=0,audit_identity='MATCHED',
                    audit_metadata_access='VERIFIED',content_read='NOT_TESTED',
                    write_capability='NOT_TESTED',complete_grant_inventory='NOT_PROVEN')
    finally:conn.close()


def main():
    if os.environ.get('NOTION_AUDIT_READ_CONFIRMED')!='true':
        print('{"result":"SKIPPED"}');return 2
    try:result=probe(os.environ.pop('NOTION_SANDBOX_TOKEN',''))
    except Hold as error:
        codes={'TOKEN_INVALID','TOKEN_REJECTED','ACCESS_FORBIDDEN','PAGE_UNAVAILABLE',
               'RATE_LIMITED','HTTP_NOT_OK','MALFORMED_RESPONSE','TARGET_NOT_VERIFIED'}
        reason=str(error) if str(error) in codes else 'PROBE_UNAVAILABLE'
        print(json.dumps(dict(result='BLOCKED',reason=reason)));return 2
    except Exception:
        print('{"result":"BLOCKED","reason":"PROBE_UNAVAILABLE"}');return 2
    print(json.dumps(result,sort_keys=True));return 0


if __name__=='__main__':raise SystemExit(main())
