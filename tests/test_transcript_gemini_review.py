import hashlib
import unittest
from nexus_sandbox.transcript_gemini_review import GeminiReview, validate_gemini_review

SOURCE="a"*64
REF="notion:page-1"
TEXT="Independent review: no critical findings."

def review(**kw):
    data=dict(source_sha256=SOURCE,source_ref=REF,model="gemini-3.5-flash-lite",
              review_text=TEXT,review_sha256=hashlib.sha256(TEXT.encode()).hexdigest(),
              invocation_id="github-run-1")
    data.update(kw)
    return GeminiReview(**data)

class GeminiReviewBindingTests(unittest.TestCase):
    def test_bound_review(self):
        self.assertEqual(validate_gemini_review(review(),source_sha256=SOURCE,source_ref=REF)["invocation_id"],"github-run-1")
    def test_wrong_source(self):
        with self.assertRaises(ValueError):
            validate_gemini_review(review(source_sha256="b"*64),source_sha256=SOURCE,source_ref=REF)
    def test_wrong_destination(self):
        with self.assertRaises(ValueError):
            validate_gemini_review(review(source_ref="notion:other"),source_sha256=SOURCE,source_ref=REF)
    def test_changed_review_text(self):
        with self.assertRaises(ValueError):
            validate_gemini_review(review(review_text="changed"),source_sha256=SOURCE,source_ref=REF)
    def test_empty_invocation(self):
        with self.assertRaises(ValueError):
            validate_gemini_review(review(invocation_id=""),source_sha256=SOURCE,source_ref=REF)
