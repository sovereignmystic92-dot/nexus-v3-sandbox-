"""Adversarial regressions for the existing offline CSF v0.2.0 adapter.

No pytest/jsonschema/network/Notion/Cortex dependency. All fixtures synthetic.
"""
import hashlib
import unittest

from nexus_sandbox.csf_transcript_ingest import ingest_candidates, segment_transcript
from nexus_sandbox.csf_v02 import CSFValidationError, make_finding, validate_finding


def candidate(segment_id="seg-0001", assertion="Synthetic port closure reported.", **extra):
    value = {
        "segment_id": segment_id,
        "assertion": assertion,
        "domain_id": "inf_supply",
        "claim_type": "observation",
        "systemic_role": "structural_bottleneck",
        "confidence_level": "unassessed",
        "confidence_rationale": "Speaker-attributed synthetic claim; unverified",
    }
    value.update(extra)
    return value


class CSFAdapterAdversarialTests(unittest.TestCase):
    def test_document_digest_preserves_whitespace_and_unicode(self):
        raw = "  Café 🌊\r\n\r\nSame.  "
        source = segment_transcript("synthetic-doc", raw)
        self.assertEqual(source["content_digest"], hashlib.sha256(raw.encode("utf-8")).hexdigest())
        self.assertNotEqual(source["content_digest"], hashlib.sha256(raw.strip().encode("utf-8")).hexdigest())

    def test_repeated_ingestion_has_stable_identity(self):
        source = segment_transcript("synthetic-doc", "Synthetic port closure reported.")
        a = ingest_candidates(source, [candidate()])
        b = ingest_candidates(source, [candidate()])
        self.assertEqual(a, b)
        self.assertEqual(a[0]["idempotency_key"], b[0]["idempotency_key"])
        self.assertEqual(a[0]["finding_id"], b[0]["finding_id"])

    def test_same_assertion_different_segments_fails_closed(self):
        source = segment_transcript("synthetic-doc", "First synthetic statement.\n\nSecond synthetic statement.")
        with self.assertRaisesRegex(CSFValidationError, "conflicting records share idempotency key"):
            ingest_candidates(source, [candidate(), candidate(segment_id="seg-0002")])

    def test_unresolved_causal_reference_rejected(self):
        source = segment_transcript("synthetic-doc", "Synthetic port closure reported.")
        link = {
            "target_domain": "geo_dependencies",
            "direction": "constrains",
            "mechanism": "Unverified synthetic hypothesis",
            "evidence_refs": ["seg-9999"],
            "verification_status": "hypothesized",
        }
        with self.assertRaisesRegex(CSFValidationError, "orphan evidence reference"):
            ingest_candidates(source, [candidate(causal_links=[link])])

    def test_missing_segment_id_rejected(self):
        source = segment_transcript("synthetic-doc", "Synthetic port closure reported.")
        with self.assertRaises(CSFValidationError):
            ingest_candidates(source, [candidate(segment_id="")])

    def test_unknown_field_rejected_by_core_validator(self):
        record = make_finding(
            "synthetic-doc", "seg-0001", "Synthetic claim.", "Synthetic claim.",
            "inf_supply", "observation", "structural_bottleneck",
        )
        record["review_status"] = "approved"
        with self.assertRaisesRegex(CSFValidationError, "missing or unknown finding fields"):
            validate_finding(record)


if __name__ == "__main__":
    unittest.main()
