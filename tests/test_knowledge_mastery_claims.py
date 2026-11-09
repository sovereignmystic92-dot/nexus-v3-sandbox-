import hashlib
import unittest
from nexus_sandbox.knowledge_mastery_claims import prepare_claim_candidates

SOURCE = ("A relay is a road. The narrator suspects a trap. "
          "The archive does not confirm quantum entanglement.").encode("utf-8")
DIGEST = hashlib.sha256(SOURCE).hexdigest()
CLAIMS = [
    dict(claim_id="road", quote="A relay is a road.",
         interpretation="The narrator describes the relay as a road.",
         kind="narrator_claim"),
    dict(claim_id="uncertain", quote="The archive does not confirm quantum entanglement.",
         interpretation="Quantum entanglement remains unconfirmed by the archive.",
         kind="inference"),
]

def run(source=SOURCE, digest=DIGEST, claims=CLAIMS):
    return prepare_claim_candidates(source, expected_sha256=digest,
                                    source_id="synthetic:mass-relays", claims=claims)

class ClaimExtractionTests(unittest.TestCase):
    def test_exact_spans_and_no_promotion(self):
        result = run()
        self.assertEqual(result.status, "CANDIDATES_FOR_REVIEW")
        self.assertEqual(result.provider_writes, 0)
        self.assertFalse(result.mastery_promoted)
        for candidate in result.candidates:
            self.assertEqual(SOURCE[candidate["byte_start"]:candidate["byte_end"]].decode(),
                             candidate["evidence_quote"])
            self.assertEqual(candidate["review_status"], "pending_independent_review")
            self.assertEqual(candidate["truth_status"], "unverified")

    def test_tampered_source_rejected(self):
        self.assertEqual(run(source=SOURCE + b"!").reason, "SOURCE_DIGEST_MISMATCH")

    def test_missing_quote_rejected(self):
        altered = [dict(CLAIMS[0], quote="Unwritten evidence")]
        self.assertEqual(run(claims=altered).reason, "EVIDENCE_NOT_UNIQUE")

    def test_ambiguous_repeated_quote_rejected(self):
        source = b"repeat repeat"
        spec = [dict(CLAIMS[0], quote="repeat")]
        self.assertEqual(run(source=source, digest=hashlib.sha256(source).hexdigest(),
                             claims=spec).reason, "EVIDENCE_NOT_UNIQUE")

    def test_duplicate_claim_id_rejected(self):
        self.assertEqual(run(claims=[CLAIMS[0], CLAIMS[0]]).reason, "DUPLICATE_CLAIM_ID")

    def test_unauthorized_kind_rejected(self):
        spec = [dict(CLAIMS[0], kind="verified_fact")]
        self.assertEqual(run(claims=spec).reason, "UNKNOWN_CLAIM_KIND")

    def test_unexpected_authority_field_rejected(self):
        spec = [dict(CLAIMS[0], permission_grant=True)]
        self.assertEqual(run(claims=spec).reason, "INVALID_CLAIM_SPEC")

    def test_unicode_offsets_are_byte_offsets(self):
        source = "🛰️ Relay text.".encode("utf-8")
        spec = [dict(CLAIMS[0], quote="Relay text.")]
        result = run(source=source, digest=hashlib.sha256(source).hexdigest(), claims=spec)
        self.assertEqual(result.status, "CANDIDATES_FOR_REVIEW")
        c = result.candidates[0]
        self.assertEqual(source[c["byte_start"]:c["byte_end"]], b"Relay text.")

if __name__ == "__main__":
    unittest.main()
