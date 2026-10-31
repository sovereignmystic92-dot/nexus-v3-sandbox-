"""Synthetic negative cases for the CI credential-routing source contract."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "verify_workflows.py"
spec = importlib.util.spec_from_file_location("workflow_verifier", MODULE_PATH)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class CredentialRoutingTests(unittest.TestCase):
    def check(self, name, body, passes):
        with TemporaryDirectory() as directory:
            folder = Path(directory) / ".github" / "workflows"
            folder.mkdir(parents=True)
            (folder / name).write_text(body)
            if passes:
                self.assertTrue(verifier.verify_credential_routing(directory))
            else:
                with self.assertRaises(ValueError):
                    verifier.verify_credential_routing(directory)

    def test_no_credential_job(self):
        self.check("synthetic-acceptance.yml", "permissions: {}\n", True)

    def test_missing_permissions_rejected(self):
        self.check("synthetic-acceptance.yml", "name: test\n", False)

    def test_unauthorized_secret_rejected(self):
        self.check("synthetic-acceptance.yml",
                   "permissions: {}\nenv:\n  TOKEN: ${{ secrets.NOTION_SANDBOX_TOKEN }}\n", False)

    def test_wrong_provider_environment_rejected(self):
        self.check("gemini-smoke.yml",
                   "permissions: {}\njobs:\n  test:\n    environment: notion-sandbox\n    env:\n      KEY: ${{ secrets.GEMINI_PILOT_API_KEY }}\n", False)

    def test_unreviewed_secret_rejected(self):
        self.check("gemini-smoke.yml",
                   "permissions: {}\njobs:\n  test:\n    environment: gemini-pilot\n    env:\n      KEY: ${{ secrets.UNREVIEWED_TOKEN }}\n", False)

    def test_correct_provider_binding(self):
        self.check("gemini-smoke.yml",
                   "permissions: {}\njobs:\n  test:\n    environment: gemini-pilot\n    env:\n      KEY: ${{ secrets.GEMINI_PILOT_API_KEY }}\n", True)

    def test_explicit_github_token_rejected(self):
        self.check("synthetic-acceptance.yml",
                   "permissions: {}\nenv:\n  KEY: ${{ github.token }}\n", False)


if __name__ == "__main__":
    unittest.main()
