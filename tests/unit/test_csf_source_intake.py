import copy
import hashlib
import unittest
from nexus_sandbox.csf_source_intake import prepare_findings, prepare_source, require_review_binding
from nexus_sandbox.csf_v02 import CSFValidationError

TEXT = ("This is a hypothetical colony ship scenario with uncertain conclusions. " * 40)
DIGEST = hashlib.sha256(TEXT.encode("utf-8")).hexdigest()

class SourceIntakeTests(unittest.TestCase):
    def test_new_source_is_prepared_without_provider_or_writes(self):
        result = prepare_source(TEXT, document_id="isaac-arthur-local-001", expected_sha256=DIGEST)
        self.assertEqual(result["source_digest"], DIGEST)
        self.assertGreater(result["segment_count"], 1)
        self.assertGreater(result["review_item_count"], 0)
        self.assertFalse(result["provider_called"])
        self.assertEqual(result["external_writes"], 0)
        self.assertFalse(result["classification_performed"])

    def test_mutated_or_unpinned_source_rejected(self):
        for content, pin in [(TEXT + "changed", DIGEST), (TEXT, ""), (TEXT, "0" * 64)]:
            with self.subTest(pin=pin):
                with self.assertRaises(CSFValidationError):
                    prepare_source(content, document_id="local", expected_sha256=pin)

    def test_invalid_document_rejected(self):
        with self.assertRaises(CSFValidationError):
            prepare_source(TEXT, document_id="", expected_sha256=DIGEST)

class AssignedFindingTests(unittest.TestCase):
    def setUp(self):
        self.source = {
            "source_url": "https://app.notion.com/p/synthetic",
            "source_revision": "r1",
            "document_id": "notion:synthetic",
            "transcript": TEXT,
            "expected_sha256": DIGEST,
        }
        self.candidate = {
            "segment_id": "seg-0001",
            "assertion": "The source describes an uncertain scenario.",
            "domain_id": "gov_coordination",
            "claim_type": "scenario",
            "systemic_role": "resilience_factor",
            "confidence_level": "unassessed",
            "confidence_rationale": "Synthetic fixture pending review.",
        }

    def test_reuses_saved_assignments_in_stable_order(self):
        assignments = {"b": self.candidate, "a": self.candidate}
        first = prepare_findings(self.source, assignments)
        self.assertEqual(first, prepare_findings(self.source, dict(reversed(list(assignments.items())))))
        self.assertEqual([item["payload"]["claim_id"] for item in first], ["a", "b"])
        self.assertNotEqual(first[0]["payload"]["finding_id"], first[1]["payload"]["finding_id"])

    def test_review_is_bound_to_exact_payload(self):
        original, = prepare_findings(self.source, {"a": self.candidate})
        review = {
            "finding_id": original["payload"]["finding_id"],
            "payload_sha256": original["payload_sha256"],
        }
        require_review_binding(original, review)
        candidate = {**self.candidate, "assertion": "The scenario is uncertain."}
        changed, = prepare_findings(self.source, {"a": candidate})
        self.assertEqual(changed["payload"]["finding_id"], review["finding_id"])
        with self.assertRaises(CSFValidationError):
            require_review_binding(changed, review)
        tampered = copy.deepcopy(original)
        tampered["payload"]["assertion"] = "Changed after review."
        with self.assertRaises(CSFValidationError):
            require_review_binding(tampered, review)

    def test_rejects_missing_binding_and_orphan_segment(self):
        with self.assertRaises(CSFValidationError):
            prepare_findings(self.source, {})
        with self.assertRaises(CSFValidationError):
            prepare_findings(self.source, {"a": {**self.candidate, "segment_id": "orphan"}})


if __name__ == "__main__":
    unittest.main()
