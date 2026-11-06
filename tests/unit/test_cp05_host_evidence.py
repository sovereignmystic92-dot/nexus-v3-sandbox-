import unittest
from nexus_sandbox.cp05_host_evidence import validate_host_evidence, HostEvidenceError

GOOD = dict(origin="trusted-host", principal_ref="runner-readonly",
            provider_auth_verified=True, effective_read_grant_verified=True,
            independent_receipt_readback=True, reads=2, writes=0, run_ref="manual-123")


class HostEvidenceTests(unittest.TestCase):
    def test_shape_only_not_attestation(self):
        result = validate_host_evidence(GOOD)
        self.assertTrue(result["shape_valid_only"])
        self.assertNotIn("authenticated", result)
        self.assertNotIn("gate_passed", result)

    def test_missing_evidence(self):
        with self.assertRaises(HostEvidenceError):
            validate_host_evidence(None)

    def test_untrusted_origin(self):
        self.reject(origin="chat-connector")

    def test_missing_principal(self):
        self.reject(principal_ref="")

    def test_no_auth(self):
        self.reject(provider_auth_verified=False)

    def test_no_grant(self):
        self.reject(effective_read_grant_verified=False)

    def test_no_readback(self):
        self.reject(independent_receipt_readback=False)

    def test_no_reads(self):
        self.reject(reads=0)

    def test_write_detected(self):
        self.reject(writes=1)

    def test_missing_run(self):
        self.reject(run_ref="")

    def test_bool_reads_rejected(self):
        self.reject(reads=True)

    def test_bool_writes_rejected(self):
        self.reject(writes=False)

    def reject(self, **overrides):
        evidence = dict(GOOD, **overrides)
        with self.assertRaises(HostEvidenceError):
            validate_host_evidence(evidence)


if __name__ == "__main__":
    unittest.main()
