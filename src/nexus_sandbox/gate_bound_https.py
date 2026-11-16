"""Optional direct Cortex API GET transport for a separately authenticated host.

No write methods, token acquisition, implicit ChatGPT credential reuse, or
provider-principal attestation. A host must provision its *own* scoped OAuth
token securely and establish identity separately before this can serve CP02.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

API_ORIGIN = "https://cortex.socra.cloud"
MAX_JSON_BYTES = 1024 * 1024


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class CortexReadOnlyHTTPS:
    """Fixed-host, GET-only transport; one token held by this short-lived instance."""

    def __init__(self, token, opener=None):
        if (type(token) is not str or not token or
                token != token.strip() or any(ord(ch) < 33 or ord(ch) > 126
                                              for ch in token)):
            raise ValueError("Separate scoped OAuth credential required")
        self._token = token
        self._opener = opener if opener is not None else urllib.request.build_opener(_NoRedirect())
        if not callable(getattr(self._opener, "open", None)):
            raise ValueError("HTTPS opener required")

    def __call__(self, method, args):
        if (method not in ("context_get", "context_access") or
                type(args) is not dict or set(args) != {"name"} or
                type(args["name"]) is not str or
                not args["name"].startswith("Nexus Sandbox ") or
                len(args["name"]) > 160 or
                any(ord(ch) < 32 for ch in args["name"])):
            raise ValueError("Only pinned synthetic Cortex GET methods permitted")
        encoded = urllib.parse.quote(args["name"], safe="")
        path = "/v1/modules/" + encoded
        if method == "context_access":
            path += "/access"
        req = urllib.request.Request(
            API_ORIGIN + path, method="GET",
            headers={"Authorization": "Bearer " + self._token,
                     "Accept": "application/json"})
        try:
            with self._opener.open(req, timeout=10) as response:
                status = response.status
                content_type = response.headers.get("Content-Type", "")
                if status != 200 or content_type.split(";")[0].strip().lower() != "application/json":
                    raise ValueError("Provider returned unsupported status or content type")
                body = response.read(MAX_JSON_BYTES + 1)
                if len(body) > MAX_JSON_BYTES:
                    raise ValueError("Provider response exceeded size bound")
            decoded = json.loads(body.decode("utf-8"))
            if type(decoded) is not dict:
                raise ValueError("Provider returned invalid JSON object")
            return {"structuredContent": decoded}
        except (urllib.error.URLError, OSError, UnicodeError, ValueError) as exc:
            # Never surface server bodies, raw URLs, authorization headers or
            # token-bearing errors. Refuse retries; host must reconcile.
            raise ValueError("Cortex read-only provider request unavailable") from None
