"""Observed connector capability checks never promote permissions."""
import unittest
from nexus_sandbox.gate_bound_capability import inspect_read_capabilities


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.modules = {"data": [{"name": "V2 Nexus CP02 Permission Test",
                                  "id": "module_123", "version": 2}],
                        "has_more": False}
        self.access = {"permissions": ["module.view", "module.edit"], "is_owner": True}
        self.detail = {"name": "V2 Nexus CP02 Permission Test",
                       "version": 2, "complete": True, "truncated": False}

    def assess(self, **overrides):
        inputs = {"modules": self.modules, "access": self.access,
                  "detail": self.detail}
        inputs.update(overrides)
        return inspect_read_capabilities(**inputs)

    def test_full_observations_still_do_not_attest_identity(self):
        x = self.assess()
        self.assertEqual(x["status"], "HELD")
        self.assertIn("PROVIDER_ATTESTED_EXECUTING_IDENTITY_MISSING", x["missing"])
        self.assertFalse(x["execution_authorized"])
        self.assertEqual(x["provider_writes"], 0)

    def test_owner_session_is_not_secondary_viewer(self):
        self.assertIn("RESTRICTED_VIEWER_SESSION_NOT_OBSERVED", self.assess()["missing"])

    def test_no_detail_yields_gap(self):
        self.assertIn("EXACT_COMPLETE_PROVIDER_READBACK_NOT_VERIFIED",
                      self.assess(detail={})["missing"])

    def test_incomplete_inventory_holds(self):
        self.assertIn("COMPLETE_MODULE_INVENTORY_NOT_VERIFIED",
                      self.assess(modules={**self.modules, "has_more": True})["missing"])

    def test_wrong_module_scope_holds(self):
        self.assertIn("SYNTHETIC_MODULE_ID_AND_REVISION_NOT_VERIFIED",
                      self.assess(modules={"data": [], "has_more": False})["missing"])

    def test_invalid_permission_report_holds(self):
        self.assertIn("EFFECTIVE_MODULE_ACCESS_REPORT_MISSING",
                      self.assess(access={"permissions": "module.view", "is_owner": "true"})["missing"])

    def test_caller_supplied_principal_cannot_authorize(self):
        x = self.assess(authenticated_principal="trusted-viewer")
        self.assertEqual(x["status"], "HELD")
        self.assertIn("PROVIDER_ATTESTED_EXECUTING_IDENTITY_MISSING", x["missing"])


if __name__ == "__main__":
    unittest.main()
