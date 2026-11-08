import unittest
from nexus_sandbox.cp05_destination_binding import validate_binding
from nexus_sandbox.csf_v02 import CSFValidationError
SOURCE={"notion_page_id":"4088c067-daa4-813b-b1f0-e1f1993120fb",
        "source_revision":"2026-11-07T16:58:00.000Z","source_sha256":"a"*64}
DEST={"system":"cortex","project_id":"nexus-test","object_type":"derived_output"}
class CP05BindingTests(unittest.TestCase):
    def test_bounded_offline_binding(self):
        receipt=validate_binding(SOURCE,DEST)
        self.assertEqual(receipt["status"],"CP05_BINDING_PREFLIGHT_ONLY")
        self.assertEqual(receipt["external_writes"],0)
        self.assertFalse(receipt["destination_readback_verified"])
        self.assertFalse(receipt["audit_gate_promoted"])
        self.assertEqual(receipt,validate_binding(SOURCE,DEST))
    def test_fail_closed_for_mismatched_destination_and_authorization(self):
        for src,dst,approved in [
            (SOURCE,dict(DEST,system="notion"),False),
            (SOURCE,dict(DEST,object_type="raw_transcript"),False),
            (dict(SOURCE,source_sha256="bad"),DEST,False),
            (SOURCE,DEST,True),
            (SOURCE,dict(DEST,project_id="../escape"),False)]:
            with self.assertRaises(CSFValidationError):
                validate_binding(src,dst,approved=approved)
if __name__=="__main__":
    unittest.main()
