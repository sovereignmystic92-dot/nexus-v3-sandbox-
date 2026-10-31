"""Offline negative tests for CP01/CP03 no-credential workflow assertions."""
import importlib.util
from pathlib import Path
import unittest
import tempfile

SOURCE = Path(__file__).resolve().parents[2] / "tools" / "check_cp01_cp03_boundaries.py"
spec = importlib.util.spec_from_file_location("cp01_cp03", SOURCE)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class BoundaryEvidenceTests(unittest.TestCase):
    def test_tracked_workflows_have_no_explicit_secret_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / ".github" / "workflows"
            folder.mkdir(parents=True)
            for name in audit.NO_CREDENTIAL_WORKFLOWS:
                (folder / name).write_text("name: synthetic\npermissions: {}\n")
            report = audit.inspect(root)
        self.assertTrue(report["source_checks_passed"])
        self.assertFalse(report["host_secret_exclusion_proven"])
        self.assertFalse(report["host_trust_independently_assessed"])

    def test_secret_expression_fails_closed(self):
        text = "permissions: {}\nenv:\n  KEY: ${{ secrets.EXAMPLE_KEY }}\n"
        self.assertFalse(audit.assess_workflow(text)["no_secret_context"])

    def test_github_token_context_fails_closed(self):
        text = "permissions: {}\nenv:\n  KEY: ${{ github.token }}\n"
        self.assertFalse(audit.assess_workflow(text)["no_secret_context"])

    def test_named_token_assignment_fails_closed(self):
        text = "permissions: {}\nenv:\n  GITHUB_TOKEN: placeholder\n"
        self.assertFalse(audit.assess_workflow(text)["no_known_token_env_assignment"])

    def test_missing_permissions_fails_closed(self):
        self.assertFalse(audit.assess_workflow("name: test\n")["explicit_no_write_permissions"])


if __name__ == "__main__":
    unittest.main()
