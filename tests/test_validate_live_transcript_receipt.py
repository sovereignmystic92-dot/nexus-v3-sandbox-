import unittest
from tools.validate_live_transcript_receipt import validate

def fixture():
    return dict(schema="NEXUS_LIVE_TRANSCRIPT_RECEIPT_V1",event_id="evt-1",
                source_ref="notion:source",source_sha256="a"*64,source_byte_count=123,
                idempotency_key="idemp-1",github_run_id=12345,github_run_attempt=1,
                policy_version="v1",authorization="ALLOW",
                notion_source_id="notion-id",cortex_module_id="module-id",
                source_readback=True,output_readback=True,duplicate_creations=0,status="PASS")

class ReceiptTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate(fixture())["status"], "PASS")
    def test_missing(self):
        d=fixture(); del d["source_sha256"]
        with self.assertRaises(ValueError): validate(d)
    def test_unknown_raw_text(self):
        d=fixture(); d["raw_transcript"]="sensitive"
        with self.assertRaises(ValueError): validate(d)
    def test_denied_cannot_pass(self):
        d=fixture(); d["authorization"]="DENY"
        with self.assertRaises(ValueError): validate(d)
    def test_failed_readback_cannot_pass(self):
        d=fixture(); d["source_readback"]=False
        with self.assertRaises(ValueError): validate(d)
    def test_duplicate_cannot_pass(self):
        d=fixture(); d["duplicate_creations"]=1
        with self.assertRaises(ValueError): validate(d)
    def test_bad_hash(self):
        d=fixture(); d["source_sha256"]="invalid"
        with self.assertRaises(ValueError): validate(d)
    def test_boolean_byte_count(self):
        d=fixture(); d["source_byte_count"]=True
        with self.assertRaises(ValueError): validate(d)

if __name__=="__main__": unittest.main()
