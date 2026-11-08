import unittest
from nexus_sandbox.cp05_live_evidence import assess_cp05
from nexus_sandbox.csf_v02 import CSFValidationError

E={"binding_sha256":"a"*64,"runner_principal":"runner-identity",
   "destination_owner":"owner-identity","permission_verified":True,
   "write_attempted":True,"write_succeeded":True,
   "readback_matched":True,"source_link_verified":True,
   "idempotency_verified":True}
GRANT={"principal":"runner-identity","destination_owner":"owner-identity",
       "binding_sha256":"a"*64,"read_allowed":True,"write_allowed":True,
       "active":True}

class CP05EvidenceTests(unittest.TestCase):
    def test_standing_grant_reuse_without_repeated_approval(self):
        r=assess_cp05(E,standing_grant=GRANT)
        self.assertEqual(r["status"],"CP05_EVIDENCE_COMPLETE")
        self.assertFalse(r["requires_exception_review"])
        self.assertFalse(r["audit_gate_promoted"])
    def test_missing_grant_or_readback_requires_exception(self):
        for evidence,grant in [(E,None),(dict(E,readback_matched=False),GRANT),
                               (E,dict(GRANT,active=False)),
                               (E,dict(GRANT,principal="other")),
                               (E,dict(GRANT,write_allowed=False)),
                               (E,dict(GRANT,binding_sha256="b"*64))]:
            r=assess_cp05(evidence,standing_grant=grant)
            self.assertEqual(r["status"],"CP05_EVIDENCE_INCOMPLETE")
            self.assertTrue(r["requires_exception_review"])
    def test_rejects_inconsistent_or_malformed_evidence(self):
        for evidence in [dict(E,write_attempted=False),
                         dict(E,readback_matched="true"),
                         dict(E,runner_principal=""),
                         dict(E,binding_sha256="bad"),
                         {k:v for k,v in E.items() if k!="destination_owner"}]:
            with self.assertRaises(CSFValidationError):
                assess_cp05(evidence,standing_grant=GRANT)
        with self.assertRaises(CSFValidationError):
            assess_cp05(E,standing_grant=dict(GRANT,active="true"))
if __name__=="__main__":
    unittest.main()
