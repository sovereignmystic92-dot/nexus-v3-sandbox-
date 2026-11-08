"""Bounded Socra installed-principal identity check. No Cortex mutation."""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def post(url, data, headers):
    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with opener.open(request, timeout=12) as response:
        if response.status != 200:
            raise ValueError("unexpected HTTP status")
        body = response.read(16385)
        if len(body) > 16384:
            raise ValueError("oversized response")
        result = json.loads(body)
        if not isinstance(result, dict):
            raise ValueError("invalid JSON object")
        return result

def main():
    client = os.environ.get("SOCRA_CLIENT_ID", "")
    secret = os.environ.get("SOCRA_CLIENT_SECRET", "")
    principal = os.environ.get("SOCRA_PRINCIPAL_ID", "")
    if not client or not secret or not re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", principal):
        raise ValueError("missing credentials or invalid raw installation principal UUID")
    payload = urllib.parse.urlencode({"grant_type":"client_credentials", "client_id":client, "client_secret":secret, "principal_id":principal}).encode()
    token = post("https://oauth.socra.cloud/oauth/token", payload, {"Content-Type":"application/x-www-form-urlencoded"})
    access = token.get("access_token")
    if not isinstance(access, str) or not access or str(token.get("token_type","")).lower() != "bearer":
        raise ValueError("token exchange did not yield bearer token")
    identity = post("https://account.socra.cloud/directory/v1/users/me", b"{}", {"Authorization":"Bearer "+access,"Content-Type":"application/json"})
    # The documented directory response may wrap member details; fail closed unless explicit fields are present.
    member = identity.get("data", identity)
    if not isinstance(member, dict) or member.get("type") != "app" or member.get("role") != "member":
        raise ValueError("directory identity not verified as installed app member")
    expected_id = os.environ.get("SOCRA_EXPECTED_DIRECTORY_ID", "")
    if not re.fullmatch(r"user_[A-Za-z0-9_-]+", expected_id) or member.get("id") != expected_id:
        raise ValueError("directory identity mismatch")
    print("PASS: installed Socra app identity verified; Cortex resource access NOT TESTED")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
        f.write("PASS: Socra installed-app identity verified. Cortex access and writes NOT TESTED.\n")

if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        # Never emit raw exception: HTTP error strings or URLs can expose details.
        print("BLOCKED: Socra installed-principal identity check did not verify")
        sys.exit(1)
