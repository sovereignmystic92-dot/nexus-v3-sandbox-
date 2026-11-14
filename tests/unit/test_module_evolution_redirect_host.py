"""Regression checks for GitHub artifact redirect host authorization."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from email.message import Message

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_github_transport import archive_get


class FakeRedirectOpener:
    def open(self, request, timeout=None):
        headers = Message()
        headers["Location"] = "https://productionresultssa16.blob.core.windows.net/verified/path?sig=not-a-real-signature"
        raise HTTPError(request.full_url, 302, "redirect", headers, None)


class FakeResponse:
    status = 200
    headers = {"Content-Length": "3"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, count=-1):
        return b"zip"


class FakeStorageOpener:
    def open(self, request, timeout=None):
        if request.headers.get("Authorization") is not None:
            raise AssertionError("token leaked to storage host")
        return FakeResponse()


class RedirectHostTests(unittest.TestCase):
    def test_observed_host_accepted_without_bearer_token(self):
        with patch("module_evolution_github_transport.urllib.request.build_opener", return_value=FakeStorageOpener()):
            self.assertEqual(archive_get("/repos/a/b/actions/artifacts/1/zip", "test-token",
                                         opener=FakeRedirectOpener()), b"zip")

    def test_unrelated_storage_host_rejected(self):
        class Other(FakeRedirectOpener):
            def open(self, request, timeout=None):
                headers = Message()
                headers["Location"] = "https://productionresultssa17.blob.core.windows.net/other?sig=x"
                raise HTTPError(request.full_url, 302, "redirect", headers, None)
        with self.assertRaisesRegex(ValueError, "untrusted artifact redirect host"):
            archive_get("/repos/a/b/actions/artifacts/1/zip", "test-token", opener=Other())


if __name__ == "__main__":
    unittest.main()
