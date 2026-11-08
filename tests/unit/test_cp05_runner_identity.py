import unittest
from nexus_sandbox.cp05_runner_identity import validate_runner_identity
from nexus_sandbox.csf_v02 import CSFValidationError

IDENTITY={"provider":"socra","principal_id":"user_123",
          "installation_id":"install_123","owner_id":"owner_123"}

class RunnerIdentityTests(unittest.TestCase):
    def test_matching_identity_is_not_live_attestation(self):
        receipt=validate_runner_identity(observed=IDENTITY,expected=IDENTITY)
        self.assertTrue(receipt["identity_matched"])
        self.assertFalse(receipt["provider_attestation_verified"])
        self.assertFalse(receipt["audit_gate_promoted"])
    def test_mismatch_and_missing_fields_fail_closed(self):
        for observed in [dict(IDENTITY,installation_id="install_other"),
                         dict(IDENTITY,provider="github"),
                         dict(IDENTITY,owner_id=""),
                         {k:v for k,v in IDENTITY.items() if k!="principal_id"}]:
            with self.assertRaises(CSFValidationError):
                validate_runner_identity(observed=observed,expected=IDENTITY)
if __name__=="__main__":
    unittest.main()
