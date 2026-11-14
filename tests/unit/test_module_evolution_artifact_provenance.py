"""Checkpoint provenance tests, using caller-supplied authenticated metadata fixtures."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_artifact_provenance import verify


class ArtifactProvenanceTests(unittest.TestCase):
    def setUp(self):
        payload = {"schema": "module_evolution_snapshot_v1", "receipts": []}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        snapshot = {"payload": payload, "sha256": hashlib.sha256(canonical.encode()).hexdigest()}
        self.data = (json.dumps(snapshot) + "\n").encode()
        self.digest = hashlib.sha256(self.data).hexdigest()
        self.metadata = {
            "repository": "sovereignmystic92-dot/nexus-v3-sandbox-",
            "workflow_path": ".github/workflows/module-evolution-daily-observation.yml",
            "run_id": 123, "run_attempt": 1, "run_conclusion": "success",
            "head_sha": "a" * 40, "artifact_name": "nexus-module-daily-123-1",
            "artifact_expired": False, "artifact_run_id": 123
        }

    def test_valid_fixture_is_not_transport_authentication(self):
        result = verify(self.metadata, self.data, self.digest)
        self.assertFalse(result["transport_authenticated"])
        self.assertFalse(result["readiness_advanced"])

    def test_wrong_workflow(self):
        self.metadata["workflow_path"] = ".github/workflows/other.yml"
        with self.assertRaises(ValueError):
            verify(self.metadata, self.data, self.digest)

    def test_wrong_run(self):
        self.metadata["artifact_run_id"] = 999
        with self.assertRaises(ValueError):
            verify(self.metadata, self.data, self.digest)

    def test_wrong_attempt(self):
        self.metadata["artifact_name"] = "nexus-module-daily-123-2"
        with self.assertRaises(ValueError):
            verify(self.metadata, self.data, self.digest)

    def test_failed_run(self):
        self.metadata["run_conclusion"] = "failure"
        with self.assertRaises(ValueError):
            verify(self.metadata, self.data, self.digest)

    def test_tampered_bytes(self):
        with self.assertRaises(ValueError):
            verify(self.metadata, self.data + b" ", self.digest)

    def test_untrusted_digest(self):
        with self.assertRaises(ValueError):
            verify(self.metadata, self.data, "0" * 64)

    def test_expired_artifact(self):
        self.metadata["artifact_expired"] = True
        with self.assertRaises(ValueError):
            verify(self.metadata, self.data, self.digest)

    def test_extra_metadata_rejected(self):
        self.metadata["unexpected"] = True
        with self.assertRaises(ValueError):
            verify(self.metadata, self.data, self.digest)


if __name__ == "__main__":
    unittest.main()
