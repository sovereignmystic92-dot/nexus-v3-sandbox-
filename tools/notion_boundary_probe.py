"""Positive root read, then metadata denial for one bound synthetic control."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import uuid

spec = importlib.util.spec_from_file_location('notion_read_probe', Path(__file__).with_name('notion_read_probe.py'))
read = importlib.util.module_from_spec(spec)
spec.loader.exec_module(read)
DENIED_COMMITMENT = '80a9524d71f7b7726e5054470812f49f549bdb655c6a9d34faa39bd1ebe5e37b'


def boundary(root, denied, token, connection_factory=None):
    try:
        denied = uuid.UUID(denied).hex
    except (ValueError, TypeError, AttributeError):
        raise read.ProbeHold('CONTROL_ID_INVALID') from None
    read.check(hashlib.sha256(denied.encode()).hexdigest() == DENIED_COMMITMENT,
               'CONTROL_ID_MISMATCH')
    read.check(uuid.UUID(root).hex != denied, 'CONTROL_EQUALS_ROOT')
    read.probe(root, token, connection_factory)
    factory = connection_factory or read.http.client.HTTPSConnection
    conn = factory('api.notion.com', port=443, timeout=10, context=read.ssl.create_default_context())
    try:
        conn.request('GET', '/v1/pages/' + denied, headers={
            'Authorization':'Bearer ' + token, 'Notion-Version':'2022-06-28',
            'Accept':'application/json'})
        response = conn.getresponse()
        # Discard the control response body even if unexpectedly accessible.
        read.check(response.status != 200, 'CONTROL_ACCESSIBLE')
        read.check(response.status == 404, 'CONTROL_DENIAL_INCONCLUSIVE')
    finally:
        conn.close()
    return {'operation':'READ_ONLY', 'requests':2, 'writes':0,
            'allowed_root':'MATCHED', 'unshared_control':'NOT_ACCESSIBLE_404',
            'scope':'one positive and one negative synthetic page sample',
            'complete_grant_inventory':'NOT_PROVEN', 'integration_acceptance':'NOT_PROVEN'}


def main():
    if os.environ.get('NOTION_BOUNDARY_PROBE_CONFIRMED') != 'true':
        print('{"result":"SKIPPED"}'); return 2
    try:
        result = boundary(os.environ.pop('NOTION_SANDBOX_ROOT_ID',''),
                          os.environ.pop('NOTION_SANDBOX_DENIED_PAGE_ID',''),
                          os.environ.pop('NOTION_SANDBOX_TOKEN',''))
    except read.ProbeHold as exc:
        codes={'CONTROL_ID_INVALID','CONTROL_ID_MISMATCH','CONTROL_EQUALS_ROOT',
               'CONTROL_ACCESSIBLE','CONTROL_DENIAL_INCONCLUSIVE'}
        reason=str(exc) if str(exc) in codes else 'POSITIVE_READ_BLOCKED'
        print(json.dumps({'result':'BLOCKED','reason':reason})); return 2
    except Exception:
        print('{"result":"BLOCKED","reason":"BOUNDARY_CHECK_INCOMPLETE"}'); return 2
    print(json.dumps(result,sort_keys=True)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
