"""Bounded Socra installed-principal identity check. No Cortex mutation."""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

class ProbeBlocked(ValueError):
    """A fixed diagnostic code safe to publish in a job log."""


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

def checked_post(stage, url, data, headers):
    try:
        return post(url, data, headers)
    except (ValueError, urllib.error.URLError, TimeoutError, OSError):
        raise ProbeBlocked(stage) from None


def main():
    client = os.environ.get("SOCRA_CLIENT_ID", "")
    secret = os.environ.get("SOCRA_CLIENT_SECRET", "")
    principal = os.environ.get("SOCRA_PRINCIPAL_ID", "")
    expected_id = os.environ.get("SOCRA_EXPECTED_DIRECTORY_ID", "")
    if not client or not secret:
        raise ProbeBlocked("CLIENT_CREDENTIALS_MISSING")
    if not re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", principal):
        raise ProbeBlocked("PRINCIPAL_UUID_MISSING_OR_INVALID")
    if not re.fullmatch(r"user_[A-Za-z0-9_-]+", expected_id):
        raise ProbeBlocked("EXPECTED_DIRECTORY_ID_MISSING_OR_INVALID")
    payload = urllib.parse.urlencode({"grant_type":"client_credentials", "client_id":client, "client_secret":secret, "principal_id":principal}).encode()
    token = checked_post("TOKEN_EXCHANGE_FAILED", "https://oauth.socra.cloud/oauth/token", payload, {"Content-Type":"application/x-www-form-urlencoded"})
    access = token.get("access_token")
    if not isinstance(access, str) or not access or str(token.get("token_type","")).lower() != "bearer":
        raise ProbeBlocked("BEARER_TOKEN_INVALID")
    identity = checked_post("DIRECTORY_LOOKUP_FAILED", "https://account.socra.cloud/directory/v1/users/me", b"{}", {"Authorization":"Bearer "+access,"Content-Type":"application/json"})
    # The documented directory response may wrap member details; fail closed unless explicit fields are present.
    member = identity.get("data", identity)
    if not isinstance(member, dict) or member.get("type") != "app" or member.get("role") != "member":
        raise ProbeBlocked("DIRECTORY_APP_MEMBER_UNVERIFIED")
    if member.get("id") != expected_id:
        raise ProbeBlocked("DIRECTORY_ID_MISMATCH")
    print("PASS: installed Socra app identity verified; Cortex resource access NOT TESTED")
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
        f.write("PASS: Socra installed-app identity verified. Cortex access and writes NOT TESTED.\n")

def cli():
    try:
        main()
    except ProbeBlocked as exc:
        print(f"BLOCKED: Socra installed-principal identity check did not verify [{exc}]")
        return 1
    except (ValueError, KeyError, OSError):
        print("BLOCKED: Socra installed-principal identity check did not verify [LOCAL_PROBE_ERROR]")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(cli())
