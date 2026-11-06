"""Read-only Socra Cortex HTTP transport. Token acquisition is host-owned.

Only documented GET endpoints are allowed. This module does not prove OAuth
installation identity or CP05 acceptance and performs no provider writes.
"""
import json
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPRedirectHandler


class CortexReadError(RuntimeError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CortexReadOnlyHTTP:
    BASE = "https://cortex.socra.cloud"
    MAX_BYTES = 1024 * 1024

    def __init__(self, token, *, opener=None):
        if not isinstance(token, str) or not token.strip() or any(c.isspace() for c in token):
            raise ValueError("Host-provided access token required")
        self._token = token
        self._opener = opener if opener is not None else build_opener(_NoRedirect())

    def _get(self, path):
        req = Request(self.BASE + path, method="GET", headers={
            "Authorization": "Bearer " + self._token,
            "Accept": "application/json",
        })
        try:
            with self._opener.open(req, timeout=10) as response:
                if response.geturl() != self.BASE + path or response.status != 200:
                    raise CortexReadError("Unexpected Cortex response")
                raw = response.read(self.MAX_BYTES + 1)
                if len(raw) > self.MAX_BYTES:
                    raise CortexReadError("Cortex response too large")
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise CortexReadError("Malformed Cortex response")
                return value
        except CortexReadError:
            raise
        except Exception:
            # Never expose a token, URL query, or provider error body in logs.
            raise CortexReadError("Cortex read failed") from None

    @staticmethod
    def _name(name):
        if not isinstance(name, str) or not name.strip() or len(name) > 256:
            raise ValueError("Exact module name required")
        return quote(name, safe="")

    def read_module(self, name, expected_id):
        encoded = self._name(name)
        if not isinstance(expected_id, str) or not expected_id.startswith("module_"):
            raise ValueError("Exact module ID required")
        access = self._get("/v1/modules/" + encoded + "/access")
        permissions = access.get("permissions")
        if not isinstance(permissions, list) or "module.view" not in permissions:
            raise CortexReadError("Effective module.view grant missing")
        module = self._get("/v1/modules/" + encoded)
        if (module.get("id") != expected_id or module.get("name") != name
                or type(module.get("version")) is not int or module["version"] < 1
                or not isinstance(module.get("content"), str)
                or module.get("archived") is not False
                or not isinstance(module.get("dependencies"), list)):
            raise CortexReadError("Cortex identity or content mismatch")
        return module
