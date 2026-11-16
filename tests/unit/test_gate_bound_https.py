"""Direct read-only HTTPS transport regressions using an offline fake opener."""
import json
import unittest
from nexus_sandbox.gate_bound_https import CortexReadOnlyHTTPS, API_ORIGIN


class Response:
    status = 200
    headers = {"Content-Type": "application/json"}
    def __init__(self, obj):
        self.obj = obj
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, n):
        return json.dumps(self.obj).encode("utf-8")[:n]


class Opener:
    def __init__(self, obj=None):
        self.requests = []
        self.obj = {} if obj is None else obj
    def open(self, request, timeout):
        self.requests.append((request, timeout))
        return Response(self.obj)


class CortexHTTPSReadTests(unittest.TestCase):
    def setUp(self):
        self.opener = Opener({"permissions": ["module.view"], "is_owner": False})
        self.client = CortexReadOnlyHTTPS("test-token", opener=self.opener)

    def test_same_token_fixed_host_get_only(self):
        r = self.client("context_access", {"name": "Nexus Sandbox CP02"})
        self.assertEqual(r["structuredContent"]["is_owner"], False)
        request, timeout = self.opener.requests[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(timeout, 10)
        self.assertEqual(request.full_url,
                         API_ORIGIN + "/v1/modules/Nexus%20Sandbox%20CP02/access")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")

    def test_get_module_path_and_no_other_verbs(self):
        self.client("context_get", {"name": "Nexus Sandbox CP02"})
        self.assertEqual(self.opener.requests[0][0].get_method(), "GET")
        for method in ("context_update", "context_create", "context_delete", "dispatch"):
            with self.assertRaises(ValueError):
                self.client(method, {"name": "Nexus Sandbox CP02"})
        self.assertEqual(len(self.opener.requests), 1)

    def test_no_unpinned_targets(self):
        for name in ("Production", "Nexus Sandbox\nInjection", "../root"):
            with self.assertRaises(ValueError):
                self.client("context_get", {"name": name})
        self.assertEqual(self.opener.requests, [])

    def test_missing_or_invalid_token(self):
        for token in ("", " token", "bad\nvalue", None):
            with self.assertRaises(ValueError):
                CortexReadOnlyHTTPS(token, opener=self.opener)

    def test_refuses_non_object_and_oversize(self):
        for obj in ([], "string"):
            self.client._opener = Opener(obj)
            with self.assertRaises(ValueError):
                self.client("context_get", {"name": "Nexus Sandbox CP02"})

    def test_provider_error_sanitized(self):
        class Fail:
            def open(self, req, timeout):
                raise OSError("test-token secret private")
        self.client._opener = Fail()
        with self.assertRaisesRegex(ValueError, "^Cortex read-only provider request unavailable$"):
            self.client("context_get", {"name": "Nexus Sandbox CP02"})


if __name__ == "__main__":
    unittest.main()
