import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_authenticated_recovery import recover, fetch_and_recover


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        payload = {"schema": "module_evolution_snapshot_v1", "receipts": []}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        checkpoint = json.dumps({"payload": payload, "sha256": hashlib.sha256(canonical.encode()).hexdigest()}).encode()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for name in ("checkpoint.json", "event.json", "receipt.json", "report.json"):
                z.writestr(name, checkpoint if name == "checkpoint.json" else "{}")
        self.archive = buf.getvalue()
        self.run = {"id": 42, "status": "completed", "conclusion": "success",
                    "event": "workflow_dispatch", "run_attempt": 1,
                    "path": ".github/workflows/module-evolution-daily-observation.yml",
                    "head_sha": "a" * 40,
                    "repository": {"full_name": "sovereignmystic92-dot/nexus-v3-sandbox-"}}
        self.artifact = {"id": 3, "name": "nexus-module-daily-42-1",
                         "expired": False, "workflow_run": {"id": 42},
                         "digest": "sha256:" + hashlib.sha256(self.archive).hexdigest()}

    def test_verified_archive(self):
        result = recover(self.run, self.artifact, self.archive, 42)
        self.assertTrue(result["archive_digest_verified"])
        self.assertFalse(result["provenance"]["readiness_advanced"])

    def test_wrong_run(self):
        with self.assertRaises(ValueError):
            recover(self.run, self.artifact, self.archive, 43)

    def test_wrong_workflow(self):
        self.run["path"] = "other.yml"
        with self.assertRaises(ValueError):
            recover(self.run, self.artifact, self.archive, 42)

    def test_archive_tamper(self):
        with self.assertRaises(ValueError):
            recover(self.run, self.artifact, self.archive + b"x", 42)

    def test_missing_digest_is_explicitly_unverified(self):
        del self.artifact["digest"]
        self.assertFalse(recover(self.run, self.artifact, self.archive, 42)["archive_digest_verified"])

    def test_no_token_no_network(self):
        calls = []
        with self.assertRaises(ValueError):
            fetch_and_recover(42, "", lambda *args: calls.append(args), lambda *args: calls.append(args))
        self.assertEqual(calls, [])

    def test_transport_injection(self):
        def api(path, token):
            self.assertEqual(token, "fixture")
            return self.run if path.endswith("/42") else {"artifacts": [self.artifact]}
        def archive(path, token):
            self.assertTrue(path.endswith("/3/zip"))
            return self.archive
        result = fetch_and_recover(42, "fixture", api, archive)
        self.assertEqual(result["provenance"]["run_id"], 42)

    def test_duplicate_artifact_fails_closed(self):
        def api(path, token):
            return self.run if path.endswith("/42") else {"artifacts": [self.artifact, self.artifact]}
        with self.assertRaises(ValueError):
            fetch_and_recover(42, "fixture", api, lambda *args: self.archive)


if __name__ == "__main__":
    unittest.main()
