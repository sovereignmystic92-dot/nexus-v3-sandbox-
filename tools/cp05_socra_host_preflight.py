"""Manual, read-only Socra app-principal preflight. No credentials in receipts."""
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

NAME = "NEXUS CP05 SYNTHETIC CORTEX READBACK 2026-11-04 A"
ID = "module_01m6kzebbfdk4ptbsg88gsf0ja"
PAYLOAD = "The copper lantern stays lit at dawn."
NOTION_ID = "40e8c067-daa4-8199-9f12-c9b6486de444"

def request(url, *, token=None, form=None, json_body=None):
    headers = {"Accept": "application/json"}
    data = None
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)

def main():
    receipt = {"checkpoint": "CP05", "mode": "READ_ONLY", "writes": 0,
               "attestation": "NOT_ATTESTED", "run_id": os.getenv("GITHUB_RUN_ID"),
               "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
               "commit": os.getenv("GITHUB_SHA"),
               "timestamp": datetime.now(timezone.utc).isoformat()}
    try:
        keys = ("SOCRA_CLIENT_ID", "SOCRA_CLIENT_SECRET", "SOCRA_PRINCIPAL_ID")
        if any(not os.getenv(k) for k in keys):
            raise ValueError("Required Socra credential missing")
        auth = request("https://oauth.socra.cloud/oauth/token", form={
            "grant_type": "client_credentials",
            "client_id": os.environ["SOCRA_CLIENT_ID"],
            "client_secret": os.environ["SOCRA_CLIENT_SECRET"],
            "principal_id": os.environ["SOCRA_PRINCIPAL_ID"]})
        token = auth.get("access_token")
        if not isinstance(token, str) or not token:
            raise ValueError("Token response invalid")
        # Confirm effective identity from the provider, not a caller-provided flag.
        identity = request("https://account.socra.cloud/directory/v1/users/me",
                           token=token, json_body={})
        if identity.get("type") != "app" or identity.get("role") != "member":
            raise ValueError("Unexpected provider principal type/role")
        receipt["directory_id"] = identity.get("id")
        access = request("https://cortex.socra.cloud/v1/modules/" +
                         urllib.parse.quote(NAME, safe="") + "/access", token=token)
        if "module.view" not in access.get("permissions", []):
            raise ValueError("Module view permission missing")
        record = request("https://cortex.socra.cloud/v1/modules/" +
                         urllib.parse.quote(NAME, safe=""), token=token)
        if (record.get("id") != ID or record.get("name") != NAME or
                record.get("version") != 1 or record.get("archived") is not False or
                not isinstance(record.get("content"), str) or
                PAYLOAD not in record["content"] or NOTION_ID not in record["content"]):
            raise ValueError("Exact synthetic fixture mismatch")
        receipt["module_id"] = ID
        receipt["version"] = record["version"]
        receipt["content_sha256"] = hashlib.sha256(record["content"].encode()).hexdigest()
        receipt["authenticated_host_read"] = True
        receipt["attestation"] = "READ_ONLY_HOST_OBSERVED"
        receipt["result"] = "PASS"
    except Exception as exc:
        # Never serialize provider responses, request bodies, or secret-bearing exceptions.
        receipt["result"] = "BLOCKED"
        receipt["failure_class"] = type(exc).__name__
    with open("cp05-socra-host-receipt.json", "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
    print("CP05 read-only preflight:", receipt["result"])
    return 0 if receipt["result"] == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
