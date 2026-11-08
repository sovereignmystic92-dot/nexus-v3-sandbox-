import unittest
from nexus_sandbox.transcript_gemini_receipt import make_receipt, verify_receipt


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.result = dict(status="GEMINI_REVIEW_OBTAINED_READ_ONLY",
                           event_id="evt-1", source_sha256="a"*64,
                           review_sha256="b"*64, model="gemini-test",
                           provider_response_id="response-1",
                           notion_writes=0, cortex_writes=0,
                           durable_receipt_verified=False)

    def make(self):
        return make_receipt(self.result, workflow_run_id="123",
                            workflow_run_attempt="1", commit_sha="c"*40)

    def test_valid_receipt(self):
        self.assertTrue(verify_receipt(self.make()))

    def test_tampering_blocked(self):
        receipt = self.make()
        receipt["event_id"] = "other"
        with self.assertRaises(ValueError):
            verify_receipt(receipt)

    def test_unexpected_content_blocked(self):
        receipt = self.make()
        receipt["review_text"] = "must never persist"
        with self.assertRaises(ValueError):
            verify_receipt(receipt)

    def test_provider_writes_blocked(self):
        self.result["cortex_writes"] = 1
        with self.assertRaises(ValueError):
            self.make()

    def test_missing_response_blocked(self):
        self.result["provider_response_id"] = ""
        with self.assertRaises(ValueError):
            self.make()

    def test_failure_blocked(self):
        self.result["status"] = "BLOCKED"
        with self.assertRaises(ValueError):
            self.make()


if __name__ == "__main__":
    unittest.main()
