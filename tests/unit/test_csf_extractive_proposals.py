import unittest
from nexus_sandbox.csf_transcript_ingest import segment_transcript_bounded
from nexus_sandbox.csf_extractive_proposals import propose_excerpts
from nexus_sandbox.csf_v02 import CSFValidationError


class ExtractiveProposalTests(unittest.TestCase):
    def test_offsets_and_unverified_labels(self):
        raw = ("This is a synthetic sentence containing a source statement for later review. " * 50)
        bounded = segment_transcript_bounded("synthetic", raw, 300)
        result = propose_excerpts(raw, bounded)
        self.assertGreater(result["proposal_count"], 0)
        self.assertFalse(result["classification_performed"])
        for proposal in result["proposals"]:
            self.assertEqual(proposal["review_status"], "unverified_source_statement")
            self.assertLess(proposal["start"], proposal["end"])
        self.assertEqual(result, propose_excerpts(raw, bounded))

    def test_digest_and_coverage_fail_closed(self):
        raw = "A synthetic sentence for later review. " * 40
        bounded = segment_transcript_bounded("synthetic", raw)
        with self.assertRaises(CSFValidationError):
            propose_excerpts(raw + "tampered", bounded)
        bounded["spans"]["seg-0001"]["end"] -= 1
        with self.assertRaises(CSFValidationError):
            propose_excerpts(raw, bounded)


if __name__ == "__main__":
    unittest.main()
