"""Synthetic regression coverage for revision-bound CSF identities."""

import hashlib
import unittest

from nexus_sandbox.csf_identity import bind_finding
from nexus_sandbox.csf_v02 import CSFValidationError, make_finding


class CSFIdentityTests(unittest.TestCase):
    def setUp(self):
        self.text = "  Synthetic source: port access was interrupted.\n"
        self.source = {
            "source_url": "https://app.notion.com/p/synthetic",
            "source_revision": "revision-1",
            "document_id": "notion:synthetic",
            "transcript": self.text,
            "expected_sha256": hashlib.sha256(self.text.encode()).hexdigest(),
        }

    def finding(self, assertion="Port access was interrupted.", **overrides):
        fields = {
            "document_id": self.source["document_id"],
            "segment_id": "seg-0001",
            "transcript_segment": self.text,
            "assertion": assertion,
            "domain_id": "inf_supply",
            "claim_type": "observation",
            "systemic_role": "structural_bottleneck",
        }
        return make_finding(**(fields | overrides))

    def test_exact_replay(self):
        first = bind_finding(self.source, self.finding(), claim_id="claim-1")
        second = bind_finding(self.source, self.finding(), claim_id="claim-1")
        self.assertEqual(first, second)
        self.assertEqual(first["payload"]["segment_sha256"], self.source["expected_sha256"])

    def test_rewording_preserves_identity_but_changes_review_digest(self):
        first = bind_finding(self.source, self.finding(), claim_id="claim-1")
        reworded = self.finding("Access to the port was disrupted.")
        second = bind_finding(self.source, reworded, claim_id="claim-1")
        for key in ("idempotency_key", "finding_id"):
            self.assertEqual(first["payload"][key], second["payload"][key])
        self.assertNotEqual(first["payload_sha256"], second["payload_sha256"])

    def test_distinct_claims_in_one_span_have_distinct_identity(self):
        first = bind_finding(self.source, self.finding(), claim_id="claim-1")
        second = bind_finding(self.source, self.finding(), claim_id="claim-2")
        self.assertNotEqual(first["payload"]["finding_id"], second["payload"]["finding_id"])

    def test_new_revision_has_distinct_identity_even_with_same_bytes(self):
        first = bind_finding(self.source, self.finding(), claim_id="claim-1")
        revised = {**self.source, "source_revision": "revision-2"}
        second = bind_finding(revised, self.finding(), claim_id="claim-1")
        self.assertNotEqual(first["payload"]["finding_id"], second["payload"]["finding_id"])

    def test_rejects_unverified_source_and_mismatched_findings(self):
        with self.assertRaisesRegex(CSFValidationError, "source digest mismatch"):
            bind_finding({**self.source, "expected_sha256": "a" * 64},
                         self.finding(), claim_id="claim-1")
        with self.assertRaisesRegex(CSFValidationError, "finding source binding mismatch"):
            bind_finding(self.source, self.finding(document_id="other"), claim_id="claim-1")
        with self.assertRaisesRegex(CSFValidationError, "source segment not verified"):
            bind_finding(self.source, self.finding(segment_id="seg-0002"), claim_id="claim-1")
        with self.assertRaisesRegex(CSFValidationError, "assigned claim ID required"):
            bind_finding(self.source, self.finding(), claim_id=" ")
