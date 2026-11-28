import json
import tempfile
import unittest
from pathlib import Path
from tools.gemini_mission_preflight import prepare_mission

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence/knowledge-mastery/mass-relays-20261109-candidates.json"

class GeminiMissionPreflightTests(unittest.TestCase):
    def test_prepared_is_not_dispatched(self):
        r = prepare_mission(issue_number=291, manifest_path=MANIFEST)
        self.assertEqual(r["status"], "PREPARED_NOT_DISPATCHED")
        self.assertEqual(r["source_status"], "SOURCE_NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(r["provider_calls"], 0)
        self.assertFalse(r["mastery_promoted"])

    def test_wrong_issue_rejected(self):
        self.assertEqual(prepare_mission(issue_number=292, manifest_path=MANIFEST)["reason"], "UNAPPROVED_MISSION")

    def test_live_authorization_cannot_bypass_gate(self):
        self.assertEqual(prepare_mission(issue_number=291, manifest_path=MANIFEST, live_call_authorized=True)["reason"], "LIVE_DISPATCH_NOT_IMPLEMENTED")

    def test_wrong_source_rejected(self):
        self.assertEqual(prepare_mission(issue_number=291, manifest_path=MANIFEST, source_bytes=b"tampered")["reason"], "SOURCE_DIGEST_MISMATCH")

    def test_manifest_tampering_rejected(self):
        data = json.loads(MANIFEST.read_text())
        data["source_sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "manifest.json"
            path.write_text(json.dumps(data))
            self.assertEqual(prepare_mission(issue_number=291, manifest_path=path)["reason"], "MANIFEST_BINDING_MISMATCH")

if __name__ == "__main__":
    unittest.main()
