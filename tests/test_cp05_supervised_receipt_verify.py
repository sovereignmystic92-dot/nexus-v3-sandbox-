"""Adversarial checks for the draft CP05 supervised receipt validator."""
import copy
import hashlib
import unittest

from tools.cp05_supervised_receipt_verify import validate, MODULE, PAGE, PAYLOAD


def valid_receipt():
    return {
        "schema": "NEXUS_CP05_SUPERVISED_READ_V1",
        "mode": "READ_ONLY",
        "attestation": "SOURCE_MATCHED",
        "notion_page_id": PAGE,
        "cortex_module_id": MODULE,
        "fixture_payload_sha256": hashlib.sha256(PAYLOAD.encode()).hexdigest(),
        "provider_writes": 0,
        "github_run_id": 41918014644,
        "github_job_id": 126882758186,
        "source_last_edited_at": "2026-11-04T21:14:09.277Z",
    }


class CP05ReceiptTests(unittest.TestCase):
    def test_valid_shape_only(self):
        self.assertTrue(validate(valid_receipt()))

    def test_missing_fields_fail(self):
        for key in valid_receipt():
            with self.subTest(key=key):
                receipt = valid_receipt()
                del receipt[key]
                with self.assertRaises(ValueError):
                    validate(receipt)

    def test_identity_digest_and_mode_fail(self):
        for key, bad in [
            ("notion_page_id", "wrong"), ("cortex_module_id", "wrong"),
            ("fixture_payload_sha256", "0" * 64), ("mode", "WRITE"),
            ("provider_writes", 1), ("attestation", "AUTHENTICATED"),
            ("github_run_id", 0), ("github_job_id", -1),
            ("source_last_edited_at", ""),
        ]:
            with self.subTest(key=key):
                receipt = valid_receipt()
                receipt[key] = bad
                with self.assertRaises(ValueError):
                    validate(receipt)

    def test_bool_is_not_integer_identity(self):
        for key in ("github_run_id", "github_job_id"):
            receipt = valid_receipt()
            receipt[key] = True
            with self.assertRaises(ValueError):
                validate(receipt)

    def test_boolean_zero_write_not_accepted(self):
        receipt = valid_receipt()
        receipt["provider_writes"] = False
        with self.assertRaises(ValueError):
            validate(receipt)

    def test_timestamp_must_be_parseable(self):
        receipt = valid_receipt()
        receipt["source_last_edited_at"] = "not-a-dateZ"
        with self.assertRaises(ValueError):
            validate(receipt)


if __name__ == "__main__":
    unittest.main()
