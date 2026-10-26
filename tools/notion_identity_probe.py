"""Opt-in credential identity observation; no import-time network."""
import http.client
import json
import os
import ssl
import uuid

MAX_BYTES = 65536
EXPECTED_NAME = "Nexus Sandbox"

class Hold(Exception):
    pass

def check(value):
    if not value:
        raise Hold()

def unique(pairs):
    result = {}
    for key, value in pairs:
        check(key not in result)
        result[key] = value
    return result

def probe(token, factory=None):
    check(type(token) is str and 0 < len(token) <= 4096)
    check(all(33 <= ord(c) <= 126 for c in token))
    conn = (factory or http.client.HTTPSConnection)(
        "api.notion.com", port=443, timeout=10, context=ssl.create_default_context())
    try:
        conn.request("GET", "/v1/users/me", headers={
            "Authorization": "Bearer " + token, "Notion-Version": "2022-06-28",
            "Accept": "application/json"})
        response = conn.getresponse()
        check(response.status == 200)
        check(response.getheader("Content-Type", "").split(";")[0].strip() == "application/json")
        raw = response.read(MAX_BYTES + 1)
        check(len(raw) <= MAX_BYTES)
        user = json.loads(raw, object_pairs_hook=unique)
        check(type(user) is dict and user.get("object") == "user")
        check(user.get("type") == "bot" and type(user.get("bot")) is dict)
        check(user.get("name") == EXPECTED_NAME)
        identity = str(uuid.UUID(user["id"]))
        return {"operation": "READ_ONLY", "requests": 1, "writes": 0,
                "bot_name": EXPECTED_NAME, "bot_id": identity,
                "identity_observation": "VERIFIED",
                "provider_settings_id_comparison": "NOT_PERFORMED",
                "complete_grant_inventory": "NOT_PROVEN"}
    finally:
        conn.close()

def main():
    if os.environ.get("NOTION_IDENTITY_CONFIRMED") != "true":
        print('{"result":"SKIPPED"}')
        return 2
    try:
        result = probe(os.environ.pop("NOTION_SANDBOX_TOKEN", ""))
    except Exception:
        # Never print remote bodies, owner/workspace details, tokens or exceptions.
        print('{"result":"BLOCKED","reason":"IDENTITY_NOT_VERIFIED"}')
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
