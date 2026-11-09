"""Offline tests for mastery assessment decisions."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from knowledge_mastery_policy import assess

def record(eid="e1", source="s1", level=2):
    return dict(evaluation_id=eid, subject_id="topic", source_refs=[source],
                evidence_refs=["proof"], outcome="pass",
                source_integrity_status="verified",
                review_independence_status="verified",
                contradiction_refs=[], mastery_level=level)

class MasteryPolicyTests(unittest.TestCase):
    def test_valid_candidate(self):
        self.assertEqual(assess([record()], subject_id="topic")["demonstrated_level"], 2)
    def test_duplicate_evaluation_id(self):
        self.assertEqual(len(assess([record(), record()], subject_id="topic")["accepted_evaluation_ids"]), 1)
    def test_dependent_source_not_counted(self):
        result = assess([record(), record("e2", level=5)], subject_id="topic")
        self.assertEqual(result["demonstrated_level"], 2)
    def test_failed_evaluation_not_promoted(self):
        r = record(); r["outcome"] = "fail"
        self.assertEqual(assess([r], subject_id="topic")["demonstrated_level"], 0)
    def test_unverified_source_not_promoted(self):
        r = record(); r["source_integrity_status"] = "unverified"
        self.assertEqual(assess([r], subject_id="topic")["demonstrated_level"], 0)
    def test_missing_independent_review_not_promoted(self):
        r = record(); r["review_independence_status"] = "unavailable"
        self.assertEqual(assess([r], subject_id="topic")["demonstrated_level"], 0)
    def test_contradiction_blocks(self):
        r = record(); r["contradiction_refs"] = ["c1"]
        self.assertEqual(assess([r], subject_id="topic")["demonstrated_level"], 0)
    def test_no_self_certification(self):
        self.assertEqual(assess([record()], subject_id="topic")["status"], "candidate_only")
    def test_other_subject_ignored(self):
        self.assertEqual(assess([record()], subject_id="other")["demonstrated_level"], 0)

if __name__ == "__main__":
    unittest.main()
