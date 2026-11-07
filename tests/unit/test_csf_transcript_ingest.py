"""Synthetic tests for the offline CSF transcript ingestion boundary."""
import unittest

from nexus_sandbox.csf_transcript_ingest import segment_transcript, ingest_candidates
from nexus_sandbox.csf_v02 import CSFValidationError

TEXT = "Synthetic port access was interrupted.\n\nSynthetic coordination was delayed."


def candidate(**overrides):
    data = {
        "segment_id": "seg-0001",
        "assertion": "The synthetic text reports interrupted port access.",
        "domain_id": "inf_supply",
        "claim_type": "observation",
        "systemic_role": "structural_bottleneck",
        "confidence_level": "unassessed",
        "confidence_rationale": "Synthetic fixture; independent verification pending",
    }
    data.update(overrides)
    return data


class CSFTranscriptIngestTests(unittest.TestCase):
    def test_deterministic_segments_and_digest(self):
        self.assertEqual(segment_transcript("synthetic-doc", TEXT), segment_transcript("synthetic-doc", TEXT))
        self.assertEqual(len(segment_transcript("synthetic-doc", TEXT)["segments"]), 2)

    def test_valid_candidate(self):
        source = segment_transcript("synthetic-doc", TEXT)
        records = ingest_candidates(source, [candidate()])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_reference"]["content_digest"], source["content_digest"])

    def test_idempotent_reingestion(self):
        source = segment_transcript("synthetic-doc", TEXT)
        self.assertEqual(ingest_candidates(source, [candidate(), candidate()]),
                         ingest_candidates(source, [candidate()]))

    def test_unknown_segment_rejected(self):
        with self.assertRaises(CSFValidationError):
            ingest_candidates(segment_transcript("synthetic-doc", TEXT), [candidate(segment_id="seg-9999")])

    def test_orphan_causal_evidence_rejected(self):
        link = {"target_domain": "gov_coordination", "direction": "constrains",
                "mechanism": "Synthetic hypothesis", "evidence_refs": ["seg-9999"],
                "verification_status": "hypothesized"}
        with self.assertRaises(CSFValidationError):
            ingest_candidates(segment_transcript("synthetic-doc", TEXT), [candidate(causal_links=[link])])

    def test_missing_candidate_classification_rejected(self):
        c = candidate()
        del c["claim_type"]
        with self.assertRaises(CSFValidationError):
            ingest_candidates(segment_transcript("synthetic-doc", TEXT), [c])

    def test_empty_transcript_rejected(self):
        with self.assertRaises(CSFValidationError):
            segment_transcript("synthetic-doc", "  ")

    def test_no_automatic_claims(self):
        self.assertEqual(ingest_candidates(segment_transcript("synthetic-doc", TEXT), []), [])


if __name__ == "__main__":
    unittest.main()
