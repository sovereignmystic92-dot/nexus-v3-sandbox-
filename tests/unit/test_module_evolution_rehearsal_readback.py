import hashlib
import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_rehearsal_readback import verify_rehearsal
from module_evolution_artifact_provenance import REPOSITORY, WORKFLOW


class RehearsalReadbackTests(unittest.TestCase):
    def setUp(self):
        self.run = {"id": 123, "repository": {"full_name": REPOSITORY},
                    "path": ".github/workflows/" + WORKFLOW, "status": "completed",
                    "conclusion": "success", "head_sha": "a" * 40, "run_attempt": 1}
        payload = {"schema": "module_evolution_snapshot_v1", "receipts": []}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        checkpoint = json.dumps({"payload": payload, "sha256": digest}).encode()
        evidence = {"evidence_class": "manual_rehearsal", "source_run_id": 123,
                    "source_head_sha": "a" * 40, "checkpoint_sha256": digest,
                    "archive_sha256": "b" * 64, "readiness_advanced": False,
                    "cortex_persisted": False, "scheduled_recovery_enabled": False}
        self.checkpoint, self.evidence = checkpoint, evidence

    def archive(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            z.writestr("checkpoint.json", self.checkpoint)
            z.writestr("evidence.json", json.dumps(self.evidence))
        return stream.getvalue()

    def test_verified_readback(self):
        data = self.archive()
        result = verify_rehearsal(data, hashlib.sha256(data).hexdigest(), self.run)
        self.assertEqual(result["source_run_id"], 123)
        self.assertFalse(result["cortex_persisted"])

    def test_rejects_zip_digest_mismatch(self):
        with self.assertRaisesRegex(ValueError, "ZIP digest"):
            verify_rehearsal(self.archive(), "0" * 64, self.run)

    def test_rejects_wrong_source(self):
        data = self.archive()
        with self.assertRaisesRegex(ValueError, "source run mismatch"):
            verify_rehearsal(data, hashlib.sha256(data).hexdigest(), dict(self.run, id=124))

    def test_rejects_state_promotion(self):
        self.evidence["cortex_persisted"] = True
        data = self.archive()
        with self.assertRaisesRegex(ValueError, "state promotion"):
            verify_rehearsal(data, hashlib.sha256(data).hexdigest(), self.run)

    def test_rejects_extra_members(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as z:
            z.writestr("checkpoint.json", self.checkpoint)
            z.writestr("evidence.json", json.dumps(self.evidence))
            z.writestr("untrusted.txt", "x")
        data = stream.getvalue()
        with self.assertRaisesRegex(ValueError, "ZIP members"):
            verify_rehearsal(data, hashlib.sha256(data).hexdigest(), self.run)


if __name__ == "__main__":
    unittest.main()
