import hashlib
import unittest
from tools.transcript_execution_receipt import validate


def receipt():
    h = hashlib.sha256(b"source").hexdigest()
    return {
        "schema_version": 1, "status": "VERIFIED", "trigger": "schedule",
        "run_id": "run-123",
        "source": {"id": "transcript-1", "sha256": h, "bytes": 6},
        "notion": {"object_id": "page-1", "write_ok": True, "readback_ok": True, "sha256": h},
        "cortex": {"object_id": "module-1", "write_ok": True, "readback_ok": True, "sha256": h},
    }


class ReceiptContractTests(unittest.TestCase):
    def test_verified_shape(self):
        self.assertTrue(validate(receipt()))

    def test_rejects_unverified_provider(self):
        r = receipt()
        r["cortex"]["readback_ok"] = False
        with self.assertRaises(ValueError):
            validate(r)

    def test_rejects_source_mismatch(self):
        r = receipt()
        r["notion"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate(r)

    def test_rejects_manual_as_automated(self):
        r = receipt()
        r["trigger"] = "manual_connector"
        with self.assertRaises(ValueError):
            validate(r)

    def test_rejects_bad_source_length(self):
        r = receipt()
        r["source"]["bytes"] = 0
        with self.assertRaises(ValueError):
            validate(r)

    def test_rejects_readback_without_write(self):
        r = receipt()
        r["notion"]["write_ok"] = False
        with self.assertRaises(ValueError):
            validate(r)


if __name__ == "__main__":
    unittest.main()
