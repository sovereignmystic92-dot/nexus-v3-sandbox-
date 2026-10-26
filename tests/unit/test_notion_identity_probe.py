import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
spec = importlib.util.spec_from_file_location("identity", Path(__file__).resolve().parents[2] / "tools/notion_identity_probe.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.body = json.dumps({"object":"user","type":"bot","bot":{"owner":{"email":"PRIVATE"}},"name":"Nexus Sandbox","id":"11111111-1111-1111-1111-111111111111"}).encode()
        self.status = 200
        self.calls = []
        self.closed = False
        self.content_type = "application/json"
    def factory(self, host, **kw):
        self.assertEqual(host, "api.notion.com")
        self.assertTrue(kw["context"].check_hostname)
        outer = self
        class Response:
            status = outer.status
            def getheader(self, key, default): return outer.content_type
            def read(self, size): return outer.body[:size]
        class Conn:
            def request(self, method, path, headers): outer.calls.append((method,path))
            def getresponse(self): return Response()
            def close(self): outer.closed = True
        return Conn()
    def test_only_selected_fields_and_one_get(self):
        result = m.probe("secret", self.factory)
        self.assertEqual(self.calls, [("GET","/v1/users/me")])
        self.assertTrue(self.closed)
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(result["complete_grant_inventory"], "NOT_PROVEN")
    def test_denials_redirects_and_rate_limits_never_retry(self):
        for status in (301,401,403,404,429,500):
            self.status = status; self.calls = []
            with self.assertRaises(m.Hold): m.probe("secret", self.factory)
            self.assertEqual(len(self.calls), 1)
            self.assertTrue(self.closed)
    def test_wrong_name_person_and_malformed_id_hold(self):
        original = json.loads(self.body)
        for key,value in (("name","unexpected"),("type","person"),("id","bad"),("bot",None)):
            data = dict(original); data[key] = value; self.body = json.dumps(data).encode()
            with self.assertRaises(Exception): m.probe("secret", self.factory)
    def test_duplicate_and_oversize_responses_hold(self):
        for body in (b'{"object":"user","object":"user"}', b"x" * (m.MAX_BYTES+1)):
            self.body = body
            with self.assertRaises(m.Hold): m.probe("secret", self.factory)
    def test_invalid_token_prevents_request(self):
        for token in ("", "line\nfeed", "x"*4097):
            with self.assertRaises(m.Hold): m.probe(token,self.factory)
        self.assertEqual(self.calls, [])
    def test_main_error_redacts_exception(self):
        with patch.dict(os.environ, {"NOTION_IDENTITY_CONFIRMED":"true","NOTION_SANDBOX_TOKEN":"SECRET"}), patch.object(m,"probe",side_effect=RuntimeError("SECRET PRIVATE")):
            out=io.StringIO()
            with redirect_stdout(out): self.assertEqual(m.main(),2)
            self.assertNotIn("SECRET",out.getvalue())
            self.assertNotIn("PRIVATE",out.getvalue())
    def test_default_off(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(m,"probe") as call:
            with redirect_stdout(io.StringIO()): self.assertEqual(m.main(),2)
            call.assert_not_called()
