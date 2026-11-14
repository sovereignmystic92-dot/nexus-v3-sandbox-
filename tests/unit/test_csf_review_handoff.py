import hashlib
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.csf_review_handoff import prepare_handoff, require_batch_review_binding
from nexus_sandbox.csf_v02 import CSFValidationError


class CSFReviewHandoffTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.db = Path(directory.name) / "review.sqlite"
        transcript = "Synthetic source reports a disruption."
        self.source = {
            "source_url": "https://app.notion.com/p/synthetic",
            "source_revision": "r1",
            "document_id": "notion:synthetic",
            "transcript": transcript,
            "expected_sha256": hashlib.sha256(transcript.encode()).hexdigest(),
        }
        self.candidate = {
            "segment_id": "seg-0001",
            "assertion": "The source reports a disruption.",
            "domain_id": "inf_supply",
            "claim_type": "observation",
            "systemic_role": "structural_bottleneck",
            "confidence_level": "unassessed",
            "confidence_rationale": "Synthetic fixture.",
        }

    def test_replay_recovers_assignments_from_disk(self):
        first = prepare_handoff(self.db, "batch-1", self.source, {"claim-1": self.candidate})
        self.assertEqual(prepare_handoff(self.db, "batch-1", self.source), first)
        with self.assertRaisesRegex(CSFValidationError, "assignments conflict"):
            prepare_handoff(self.db, "batch-1", self.source, {"claim-2": self.candidate})
        with self.assertRaisesRegex(CSFValidationError, "source or payload conflict"):
            prepare_handoff(self.db, "batch-1", {**self.source, "source_revision": "r2"})
        self.assertEqual(prepare_handoff(self.db, "batch-1", self.source), first)

    def test_review_must_cover_exact_batch(self):
        assignments = {"claim-1": self.candidate, "claim-2": self.candidate}
        original = prepare_handoff(self.db, "batch-1", self.source, assignments)
        reviews = [
            {"finding_id": item["payload"]["finding_id"], "payload_sha256": item["payload_sha256"]}
            for item in original
        ]
        require_batch_review_binding(original, reviews[::-1])
        with self.assertRaisesRegex(CSFValidationError, "incomplete"):
            require_batch_review_binding(original, reviews[:1])
        with self.assertRaisesRegex(CSFValidationError, "duplicate"):
            require_batch_review_binding(original, reviews[:1] * 2)
        assignments["claim-1"] = {**self.candidate, "assertion": "A disruption was reported."}
        revised = prepare_handoff(self.db, "batch-2", self.source, assignments)
        self.assertEqual(revised[0]["payload"]["finding_id"], reviews[0]["finding_id"])
        with self.assertRaisesRegex(CSFValidationError, "does not match"):
            require_batch_review_binding(revised, reviews)
