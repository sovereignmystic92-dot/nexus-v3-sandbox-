import hashlib
import io
import json
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from module_evolution_evidence_readback import validate_evidence
from module_evolution_snapshot import canonical


def make_archive():
    repo = "sovereignmystic92-dot/nexus-v3-sandbox-"
    receipts = []
    for run in (41, 42):
        event = {"repository": repo, "event": "workflow_run", "event_id": str(run) + "-1",
                 "subject": "a" * 40, "source_url": "https://github.com/" + repo + "/actions/runs/" + str(run),
                 "module_hints": []}
        event_key = hashlib.sha256(json.dumps([event[k] for k in ("repository", "event", "event_id", "subject")],
                                              separators=(",", ":")).encode()).hexdigest()
        receipts.append({"event_key": event_key, "event_json": canonical(event),
                         "modules_json": "[]", "status": "PENDING_VALIDATION"})
    receipts.sort(key=lambda r: r["event_key"])
    payload = {"schema": "module_evolution_snapshot_v1", "receipts": receipts}
    digest = hashlib.sha256(canonical(payload).encode()).hexdigest()
    evidence = {"previous_run_id": 41, "target_run_id": 42, "previous_receipts": 1,
                "new_receipts": 1, "total_receipts": 2, "checkpoint_sha256": digest,
                "evidence_class": "supervised_live", "readiness_advanced": False,
                "cortex_persisted": False, "unattended_enabled": False}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr("checkpoint.json", json.dumps({"payload": payload, "sha256": digest}))
        z.writestr("evidence.json", json.dumps(evidence))
    return buffer.getvalue()


class ReadbackTests(unittest.TestCase):
    def test_verified_two_run_evidence(self):
        archive = make_archive()
        result = validate_evidence(archive, hashlib.sha256(archive).hexdigest())
        self.assertEqual(result["receipts"], 2)
        self.assertFalse(result["unattended_enabled"])

    def test_rejects_wrong_archive_digest(self):
        with self.assertRaisesRegex(ValueError, "ZIP digest mismatch"):
            validate_evidence(make_archive(), "0" * 64)

    def test_rejects_truncated_archive(self):
        archive = make_archive()[:-40]
        with self.assertRaises(Exception):
            validate_evidence(archive, hashlib.sha256(archive).hexdigest())


if __name__ == "__main__":
    unittest.main()
