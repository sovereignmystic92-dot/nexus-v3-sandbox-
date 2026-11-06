import io
import json
import unittest
from nexus_sandbox.cp05_cortex_http import CortexReadOnlyHTTP, CortexReadError

NAME = "Nexus CP05 Synthetic"
ID = "module_fixture123"


class Response:
    status = 200
    def __init__(self, url, payload):
        self.url = url
        self.payload = json.dumps(payload).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def geturl(self):
        return self.url
    def read(self, limit):
        return self.payload[:limit]


class Opener:
    def __init__(self, access=None, module=None, redirect=False):
        self.access = access if access is not None else {"permissions": ["module.view"]}
        self.module = module if module is not None else dict(
            id=ID, name=NAME, version=1, content="fixture",
            archived=False, dependencies=[])
        self.calls = []
        self.redirect = redirect
    def open(self, req, timeout):
        self.calls.append((req.full_url, req.get_method(), timeout))
        self_test = len(self.calls) == 1
        url = req.full_url + "/redirect" if self.redirect else req.full_url
        return Response(url, self.access if self_test else self.module)


class CortexHTTPTests(unittest.TestCase):
    def client(self, **kw):
        opener = Opener(**kw)
        return CortexReadOnlyHTTP("test-token", opener=opener), opener

    def test_exact_read_and_grant(self):
        client, opener = self.client()
        self.assertEqual(client.read_module(NAME, ID)["id"], ID)
        self.assertEqual(len(opener.calls), 2)
        self.assertTrue(all(method == "GET" and timeout == 10 for _, method, timeout in opener.calls))
        self.assertTrue(opener.calls[0][0].endswith("/access"))

    def test_no_grant_blocks_content_read(self):
        client, opener = self.client(access={"permissions": []})
        with self.assertRaises(CortexReadError):
            client.read_module(NAME, ID)
        self.assertEqual(len(opener.calls), 1)

    def test_wrong_id(self):
        client, _ = self.client(module=dict(id="module_other", name=NAME,
            version=1, content="fixture", archived=False, dependencies=[]))
        with self.assertRaises(CortexReadError):
            client.read_module(NAME, ID)

    def test_archived_rejected(self):
        client, _ = self.client(module=dict(id=ID, name=NAME,
            version=1, content="fixture", archived=True, dependencies=[]))
        with self.assertRaises(CortexReadError):
            client.read_module(NAME, ID)

    def test_redirect_rejected(self):
        client, _ = self.client(redirect=True)
        with self.assertRaises(CortexReadError):
            client.read_module(NAME, ID)

    def test_token_required(self):
        with self.assertRaises(ValueError):
            CortexReadOnlyHTTP("")

    def test_invalid_module_name(self):
        client, opener = self.client()
        with self.assertRaises(ValueError):
            client.read_module("", ID)
        self.assertEqual(opener.calls, [])

    def test_boolean_version_rejected(self):
        client, _ = self.client(module=dict(id=ID, name=NAME,
            version=True, content="fixture", archived=False, dependencies=[]))
        with self.assertRaises(CortexReadError):
            client.read_module(NAME, ID)


if __name__ == "__main__":
    unittest.main()
