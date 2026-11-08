"""Offline safety checks for CP05 runner identity probe; never use real credentials."""
import importlib.util
import os
import pathlib
import unittest
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

    def test_no_redirects(self):
        handler = probe.NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, "redirect", {}, "https://example.invalid"))

if __name__ == "__main__":
    unittest.main()
