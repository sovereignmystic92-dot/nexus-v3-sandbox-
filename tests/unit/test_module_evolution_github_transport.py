import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_github_transport import api_get, archive_get, _url, _read_bounded


class Response:
    status = 200
    headers = {}
    def __init__(self, data):
        self.data = io.BytesIO(data)
    def read(self, count):
        return self.data.read(count)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class TransportTests(unittest.TestCase):
    def test_reject_external_api_path(self):
        with self.assertRaises(ValueError):
            _url("https://evil.example/")

    def test_bounded_response(self):
        with self.assertRaises(ValueError):
            _read_bounded(Response(b"1234"), 3)

    def test_api_auth_header(self):
        class Opener:
            def open(self, req, timeout):
                self.req = req
                return Response(b'{"ok":true}')
        opener = Opener()
        self.assertEqual(api_get("/repos/example/repo", "test-secret", opener), {"ok": True})
        self.assertEqual(opener.req.get_header("Authorization"), "Bearer test-secret")

    def test_redirect_rejects_untrusted_host(self):
        class Opener:
            def open(self, req, timeout):
                raise urllib.error.HTTPError(req.full_url, 302, "redirect",
                                             {"Location": "https://evil.example/a.zip"}, None)
        with self.assertRaises(ValueError):
            archive_get("/repos/example/repo/actions/artifacts/3/zip", "secret", Opener())

    def test_redirect_does_not_forward_token(self):
        class Opener:
            def open(self, req, timeout):
                raise urllib.error.HTTPError(req.full_url, 302, "redirect",
                    {"Location": "https://objects.githubusercontent.com/signed.zip"}, None)
        class Download:
            def open(self, req, timeout):
                self.req = req
                return Response(b"zip bytes")
        download = Download()
        with patch("module_evolution_github_transport.urllib.request.build_opener", return_value=download):
            data = archive_get("/repos/example/repo/actions/artifacts/3/zip", "secret", Opener())
        self.assertEqual(data, b"zip bytes")
        self.assertIsNone(download.req.get_header("Authorization"))

    def test_redirect_requires_https(self):
        class Opener:
            def open(self, req, timeout):
                raise urllib.error.HTTPError(req.full_url, 302, "redirect",
                    {"Location": "http://objects.githubusercontent.com/a.zip"}, None)
        with self.assertRaises(ValueError):
            archive_get("/repos/example/repo/actions/artifacts/3/zip", "secret", Opener())


if __name__ == "__main__":
    unittest.main()
