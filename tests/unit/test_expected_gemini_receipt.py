import unittest
from nexus_sandbox.transcript_gemini_receipt import make_receipt, verify_expected_receipt

class ExpectedReceiptTests(unittest.TestCase):
    def setUp(self):
        self.context = dict(event_id="fixture-1", source_sha256="a"*64,
                            workflow_run_id="123", workflow_run_attempt="1", commit_sha="b"*40)
        result = dict(status="GEMINI_REVIEW_OBTAINED_READ_ONLY", event_id="fixture-1",
                      source_sha256="a"*64, review_sha256="c"*64, model="synthetic",
                      provider_response_id="synthetic-response", notion_writes=0,
                      cortex_writes=0, durable_receipt_verified=False)
        self.receipt = make_receipt(result, workflow_run_id="123", workflow_run_attempt="1", commit_sha="b"*40)
    def test_matching_context(self):
        self.assertTrue(verify_expected_receipt(self.receipt, **self.context))
    def test_valid_receipt_from_other_context_holds(self):
        for key in self.context:
            with self.subTest(key=key):
                wrong = dict(self.context); wrong[key] = "other"
                with self.assertRaises(ValueError):
                    verify_expected_receipt(self.receipt, **wrong)
    def test_missing_expected_binding_holds(self):
        for key in self.context:
            with self.subTest(key=key):
                wrong = dict(self.context); wrong[key] = ""
                with self.assertRaises(ValueError):
                    verify_expected_receipt(self.receipt, **wrong)
    def test_tampered_receipt_holds(self):
        wrong = dict(self.receipt); wrong["source_sha256"] = "d"*64
        with self.assertRaises(ValueError):
            verify_expected_receipt(wrong, **self.context)
