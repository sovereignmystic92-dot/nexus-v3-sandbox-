"""Offline contract tests for Nexus Knowledge Mastery receipts (no provider calls)."""
import json
import unittest
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "knowledge_mastery_receipt_v0.1.json").read_text())

def receipt():
    return {
        "evaluation_id": "eval-1", "subject_id": "topic-1",
        "source_refs": ["notion:source-1"], "source_integrity_status": "verified",
        "revision": "rev-1", "question_or_task": "Explain claim",
        "rubric_version": "v1", "expected_or_reference": "reference",
        "observed_answer": "answer", "score": 0.8,
        "evidence_refs": ["evidence-1"], "uncertainty": "low",
        "contradiction_refs": [], "evaluator_identity": "reviewer-1",
        "review_independence_status": "verified",
        "timestamp": "2026-11-09T06:00:00Z", "outcome": "pass",
    }

@unittest.skipIf(Draft202012Validator is None, "jsonschema dependency unavailable")
class KnowledgeMasterySchemaTests(unittest.TestCase):
    def setUp(self):
        self.validator = Draft202012Validator(SCHEMA)
    def valid(self, record):
        return not list(self.validator.iter_errors(record))
    def test_valid_pass(self):
        self.assertTrue(self.valid(receipt()))
    def test_missing_provenance_rejected(self):
        record = receipt(); del record["source_refs"]
        self.assertFalse(self.valid(record))
    def test_unverified_source_cannot_pass(self):
        record = receipt(); record["source_integrity_status"] = "unverified"
        self.assertFalse(self.valid(record))
    def test_missing_independent_review_cannot_pass(self):
        record = receipt(); record["review_independence_status"] = "unavailable"
        self.assertFalse(self.valid(record))
    def test_no_evidence_cannot_pass(self):
        record = receipt(); record["evidence_refs"] = []
        self.assertFalse(self.valid(record))
    def test_duplicate_source_refs_rejected(self):
        record = receipt(); record["source_refs"].append("notion:source-1")
        self.assertFalse(self.valid(record))
    def test_unknown_permission_field_rejected(self):
        record = receipt(); record["permission_override"] = True
        self.assertFalse(self.valid(record))
    def test_inconclusive_with_unverified_source_is_recordable(self):
        record = receipt(); record["outcome"] = "inconclusive"
        record["source_integrity_status"] = "unverified"
        record["review_independence_status"] = "unavailable"
        self.assertTrue(self.valid(record))

if __name__ == "__main__":
    unittest.main()
