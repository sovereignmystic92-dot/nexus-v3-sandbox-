"""One opt-in, read-only sandbox metadata request. No import-time network."""
import hashlib
import http.client
import json
import os
import ssl
import uuid

ROOT_COMMITMENT = '244e437544a43a84802fb561f17a6def0ea2273e0631a2511d1eb52642eeec01'
EXPECTED_TITLE = 'Nexus Notion Sandbox — Synthetic Integration N01'
MAX_BYTES = 1024 * 1024


class ProbeHold(Exception):
    pass


def check(condition):
    if not condition:
        raise ProbeHold('VALIDATION_HOLD')


def probe(root, token, connection_factory=None):
    root = uuid.UUID(root).hex
    check(hashlib.sha256(root.encode()).hexdigest() == ROOT_COMMITMENT)
    check(type(token) is str and bool(token) and len(token) <= 4096)
    check(not any(ord(c) < 33 or ord(c) > 126 for c in token))
    factory = connection_factory or http.client.HTTPSConnection
    conn = factory('api.notion.com', port=443, timeout=10, context=ssl.create_default_context())
    try:
        conn.request('GET', '/v1/pages/' + root, headers={
            'Authorization': 'Bearer ' + token, 'Notion-Version': '2022-06-28',
            'Accept': 'application/json'})
        response = conn.getresponse()
        # Redirects, denials, throttling and server failures are not retried.
        check(response.status == 200)
        check(response.getheader('Content-Type', '').split(';')[0].strip() == 'application/json')
        raw = response.read(MAX_BYTES + 1)
        check(len(raw) <= MAX_BYTES)
        def unique(pairs):
            result = {}
            for key, value in pairs:
                check(key not in result); result[key] = value
            return result
        page = json.loads(raw, object_pairs_hook=unique)
        check(type(page) is dict and page.get('object') == 'page')
        check(uuid.UUID(page.get('id', '')).hex == root)
        check(page.get('archived') is False and page.get('in_trash', False) is False)
        props = page.get('properties')
        check(type(props) is dict)
        titles = [p.get('title') for p in props.values() if type(p) is dict and p.get('type') == 'title']
        check(len(titles) == 1 and type(titles[0]) is list)
        title = ''.join(part['plain_text'] for part in titles[0])
        check(title == EXPECTED_TITLE)
        return {'operation':'READ_ONLY', 'root_identity':'MATCHED', 'root_title':'MATCHED',
                'requests':1, 'writes':0, 'credential_scope':'NOT_PROVEN',
                'integration_acceptance':'NOT_PROVEN'}
    finally:
        conn.close()


def main():
    if os.environ.get('NOTION_READ_PROBE_CONFIRMED') != 'true':
        print('{"result":"SKIPPED"}')
        return 2
    try:
        result = probe(os.environ.pop('NOTION_SANDBOX_ROOT_ID', ''),
                       os.environ.pop('NOTION_SANDBOX_TOKEN', ''))
    except Exception:
        # Never emit remote bodies, private identifiers, tokens or exception text.
        print('{"result":"BLOCKED","detail":"Read probe failed; inspect configuration privately"}')
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
