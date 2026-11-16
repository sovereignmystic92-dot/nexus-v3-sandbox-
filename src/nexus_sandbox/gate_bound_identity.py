"""Provider-backed Socra installed-app identity for Cortex read-only runtime.

Setup/consent belongs to a human owner and occurs outside this module. The
runtime has its own confidential OAuth client ID, client secret, installation
principal UUID and expected Directory user_ ID. No human OAuth grant reuse.
The same issued access token verifies identity and reads Cortex. No writes.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from .gate_bound_runtime import inspect_with_cortex_oauth

TOKEN_URL = "https://oauth.socra.cloud/oauth/token"
IDENTITY_URL = "https://account.socra.cloud/directory/v1/users/me"
MAX_RESPONSE = 16384


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _post_json(request, opener):
    try:
        with opener.open(request, timeout=10) as response:
            if (response.status != 200 or
                    response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                    != "application/json"):
                raise ValueError()
            body = response.read(MAX_RESPONSE + 1)
            if len(body) > MAX_RESPONSE:
                raise ValueError()
        value = json.loads(body.decode("utf-8"))
        if type(value) is not dict:
            raise ValueError()
        return value
    except (OSError, ValueError, UnicodeError, urllib.error.URLError):
        # No exception cause: server error bodies and token-bearing request
        # objects must never appear in logs.
        raise ValueError("Socra authenticated request failed") from None


def obtain_installed_principal_token(*, client_id, client_secret, principal_id,
                                     expected_directory_id, opener=None):
    """Issue a short-lived app token and bind it to the Directory principal.

    caller must trust its private credentials store + the provider TLS boundary.
    A mocked opener is for tests only; not evidence of operational identity.
    """
    if (any(type(v) is not str or not v or len(v) > 512 or
            v != v.strip() or any(ord(ch) < 33 or ord(ch) > 126 for ch in v)
            for v in (client_id, client_secret, principal_id, expected_directory_id))
            or not client_id.startswith("client_")
            or not expected_directory_id.startswith("user_")):
        raise ValueError("Installed-principal configuration unavailable")
    if opener is None:
        opener = urllib.request.build_opener(_NoRedirect())
    payload = urllib.parse.urlencode({
        "grant_type": "client_credentials", "client_id": client_id,
        "client_secret": client_secret, "principal_id": principal_id
    }).encode("utf-8")
    req = urllib.request.Request(
        TOKEN_URL, data=payload, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"})
    result = _post_json(req, opener)
    token = result.get("access_token")
    expires = result.get("expires_in")
    if (type(token) is not str or not token or len(token) > 8192 or
            any(ord(x) < 33 or ord(x) > 126 for x in token) or
            result.get("token_type", "").lower() != "bearer" or
            type(expires) is not int or not 1 <= expires <= 3600):
        raise ValueError("Socra token response invalid")
    identity_req = urllib.request.Request(
        IDENTITY_URL, data=b"{}", method="POST",
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json", "Accept": "application/json"})
    identity = _post_json(identity_req, opener)
    # The returned ID is a user_ directory ID; principal_id is the raw
    # installation UUID. They are intentionally separate identifiers.
    if (identity.get("id") != expected_directory_id or
            identity.get("type") != "app" or
            identity.get("role") != "member"):
        raise ValueError("Installed-principal identity mismatch")
    return token, {"provider": "CORTEX", "principal": expected_directory_id,
                   "authenticated": True}


def inspect_with_installed_principal(*, client_id, client_secret, principal_id,
                                     expected_directory_id, module_name, module_id,
                                     checkpoint_statuses, applicable_gates,
                                     other_boundary_evidence, identity_opener=None,
                                     cortex_opener=None):
    """One identity-verified synthetic read, explicitly no mutation."""
    token, identity = obtain_installed_principal_token(
        client_id=client_id, client_secret=client_secret,
        principal_id=principal_id, expected_directory_id=expected_directory_id,
        opener=identity_opener)
    operation = {"id": "cp02:installed-principal-read",
                 "principal": expected_directory_id, "provider": "CORTEX",
                 "target": "synthetic:cp02", "action": "read", "synthetic": True}
    return inspect_with_cortex_oauth(
        token=token, authenticated_identity_exact=lambda: dict(identity),
        module_name=module_name, module_id=module_id, operation=operation,
        checkpoint_statuses=checkpoint_statuses, applicable_gates=applicable_gates,
        other_boundary_evidence=other_boundary_evidence, opener=cortex_opener)
