import unittest
from nexus_sandbox.cortex_host_binding import validate_host_binding, HostBindingBlocked

GOOD = dict(transaction_key="haiti-1", source_page_id="source", analysis_page_id="analysis",
            source_revision="rev1", analysis_revision="rev2",
            destination_account="account", destination_owner="owner",
            observed_account="account", observed_owner="owner",
            registry_pages=[{"digest": "a" * 64}], registry_complete=True,
            source_verified=True, analysis_verified=True,
            exclusive_worker=True, durable_journal=True)

class HostBindingTests(unittest.TestCase):
    def test_complete_readonly_evidence(self):
        self.assertEqual(validate_host_binding(**GOOD).destination_owner, "owner")

    def test_wrong_account(self):
        with self.assertRaises(HostBindingBlocked):
            validate_host_binding(**{**GOOD, "observed_account": "other"})

    def test_missing_worker_fence(self):
        with self.assertRaises(HostBindingBlocked):
            validate_host_binding(**{**GOOD, "exclusive_worker": False})

    def test_incomplete_registry(self):
        with self.assertRaises(HostBindingBlocked):
            validate_host_binding(**{**GOOD, "registry_complete": False})

    def test_missing_journal(self):
        with self.assertRaises(HostBindingBlocked):
            validate_host_binding(**{**GOOD, "durable_journal": False})

    def test_same_source_and_analysis(self):
        with self.assertRaises(HostBindingBlocked):
            validate_host_binding(**{**GOOD, "analysis_page_id": "source"})

    def test_bad_registry_evidence(self):
        with self.assertRaises(HostBindingBlocked):
            validate_host_binding(**{**GOOD, "registry_pages": [{"digest": "bad"}]})

if __name__ == "__main__":
    unittest.main()
