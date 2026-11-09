"""Validate an evidence-only claim manifest against the exact archived bytes."""
import json
import unittest
from pathlib import Path
from nexus_sandbox.knowledge_mastery_claims import prepare_claim_candidates

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evidence/knowledge-mastery/mass-relays-20261109-candidates.json"

class MassRelaysEvidenceTests(unittest.TestCase):
    def test_candidate_manifest_is_pending_and_has_no_authority(self):
        doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(doc["source_bytes"], 19000)
        self.assertEqual(len(doc["claims"]), 5)
        self.assertEqual(doc["provider_writes"], 0)
        self.assertFalse(doc["mastery_promoted"])
        for claim in doc["claims"]:
            self.assertEqual(claim["review_status"], "pending_independent_review")
            self.assertEqual(claim["truth_status"], "unverified")
            self.assertLess(claim["byte_start"], claim["byte_end"])
            self.assertEqual(claim["source_sha256"], doc["source_sha256"])

    def test_reextraction_requires_original_source_bytes(self):
        doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
        proposals = [
            {k: c[k] for k in ("claim_id", "quote", "interpretation", "kind")
             if k != "quote"} | {"quote": c["evidence_quote"]}
            for c in doc["claims"]
        ]
        # The evidence manifest alone cannot stand in for the source.
        result = prepare_claim_candidates(
            b"", expected_sha256=doc["source_sha256"],
            source_id=doc["claims"][0]["source_id"], claims=proposals)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.reason, "SOURCE_DIGEST_MISMATCH")

if __name__ == "__main__":
    unittest.main()
