import unittest
from nexus_sandbox.cp05_live_evidence import assess_cp05
from nexus_sandbox.csf_v02 import CSFValidationError
E={"binding_sha256":"a"*64,"runner_principal":"runner-identity",
   "destination_owner":"owner-identity","permission_verified":True,
   "write_attempted":True,"write_succeeded":True,
   "readback_matched":True,"source_link_verified":True,
   "idempotency_verified":True}
class CP05EvidenceTests(unittest.TestCase):
    def test_complete_evidence_still_does_not_promote_gate(self):
        r=assess_cp05(E)
        self.assertEqual(r["status"],"CP05_EVIDENCE_COMPLETE")
        self.assertFalse(r["audit_gate_promoted"])
    def test_missing_readback_is_incomplete(self):
        r=assess_cp05(dict(E,readback_matched=False))
        self.assertEqual(r["status"],"CP05_EVIDENCE_INCOMPLETE")
    def test_rejects_inconsistent_or_missing_evidence(self):
        for evidence in [dict(E,write_attempted=False),
                         dict(E,readback_matched="true"),
                         dict(E,runner_principal=""),
                         dict(E,binding_sha256="bad"),
                         {k:v for k,v in E.items() if k!="destination_owner"}]:
            with self.assertRaises(CSFValidationError):
                assess_cp05(evidence)
if __name__=="__main__":
    unittest.main()
