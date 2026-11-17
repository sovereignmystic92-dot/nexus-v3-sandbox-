"""Offline safety checks for CP05 runner identity probe; never use real credentials."""
import contextlib
import importlib.util
import io
import os
import pathlib
import unittest
import urllib.error
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cp05_identity", ROOT / "tools" / "cp05_socra_installed_principal_identity.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)

class IdentitySafetyTests(unittest.TestCase):
    def test_missing_credentials_fail_closed_before_network(self):
        with patch.dict(os.environ, {"SOCRA_CLIENT_ID":"","SOCRA_CLIENT_SECRET":"","SOCRA_PRINCIPAL_ID":""}):
            with patch.object(probe, "post", side_effect=AssertionError("network must not be called")):
                with self.assertRaises(ValueError):
                    probe.main()

    def test_invalid_principal_fail_closed_before_network(self):
        with patch.dict(os.environ, {"SOCRA_CLIENT_ID":"fake","SOCRA_CLIENT_SECRET":"fake","SOCRA_PRINCIPAL_ID":"user_not_uuid"}):
            with patch.object(probe, "post", side_effect=AssertionError("network must not be called")):
                with self.assertRaises(ValueError):
                    probe.main()

    def test_missing_directory_binding_blocks_before_network(self):
        env = {
            "SOCRA_CLIENT_ID": "synthetic-client",
            "SOCRA_CLIENT_SECRET": "synthetic-secret",
            "SOCRA_PRINCIPAL_ID": "11111111-1111-4111-8111-111111111111",
            "SOCRA_EXPECTED_DIRECTORY_ID": "",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.object(probe, "post", side_effect=AssertionError("network must not be called")):
                with self.assertRaisesRegex(probe.ProbeBlocked, "EXPECTED_DIRECTORY_ID_MISSING_OR_INVALID"):
                    probe.main()

    def test_network_failures_report_stage_without_error_details(self):
        env = {
            "SOCRA_CLIENT_ID": "synthetic-client",
            "SOCRA_CLIENT_SECRET": "synthetic-secret",
            "SOCRA_PRINCIPAL_ID": "11111111-1111-4111-8111-111111111111",
            "SOCRA_EXPECTED_DIRECTORY_ID": "user_expected",
        }
        token = {"access_token": "synthetic-token", "token_type": "Bearer"}
        for prefix, expected in (
            ([], "TOKEN_EXCHANGE_FAILED"),
            ([token], "DIRECTORY_LOOKUP_FAILED"),
        ):
            with self.subTest(stage=expected), patch.dict(os.environ, env, clear=True):
                error = urllib.error.URLError("unredacted diagnostic sentinel")
                output = io.StringIO()
                with patch.object(probe, "post", side_effect=[*prefix, error]):
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(probe.cli(), 1)
                self.assertIn(f"[{expected}]", output.getvalue())
                self.assertNotIn("unredacted diagnostic sentinel", output.getvalue())
                self.assertNotIn("synthetic-token", output.getvalue())

    def test_no_redirects(self):
        handler = probe.NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "redirect", {}, "https://example.invalid"))

    def test_wrong_directory_identity_fails_closed(self):
        env = {
            "SOCRA_CLIENT_ID": "synthetic-client",
            "SOCRA_CLIENT_SECRET": "synthetic-secret",
            "SOCRA_PRINCIPAL_ID": "11111111-1111-4111-8111-111111111111",
            "SOCRA_EXPECTED_DIRECTORY_ID": "user_expected",
        }
        responses = [
            {"access_token": "synthetic-token", "token_type": "Bearer"},
            {"type": "app", "role": "member", "id": "user_other"},
        ]
        with patch.dict(os.environ, env):
            with patch.object(probe, "post", side_effect=responses) as post:
                with self.assertRaises(ValueError):
                    probe.main()
                self.assertEqual(post.call_count, 2)

    def test_wrong_role_fails_closed(self):
        env = {
            "SOCRA_CLIENT_ID": "synthetic-client",
            "SOCRA_CLIENT_SECRET": "synthetic-secret",
            "SOCRA_PRINCIPAL_ID": "11111111-1111-4111-8111-111111111111",
            "SOCRA_EXPECTED_DIRECTORY_ID": "user_expected",
        }
        responses = [
            {"access_token": "synthetic-token", "token_type": "Bearer"},
            {"type": "app", "role": "owner", "id": "user_expected"},
        ]
        with patch.dict(os.environ, env):
            with patch.object(probe, "post", side_effect=responses):
                with self.assertRaises(ValueError):
                    probe.main()

if __name__ == "__main__":
    unittest.main()
