"""Host-scoped Cortex read: identity/grant/target before actual read."""
import unittest

from nexus_sandbox.gate_bound_adapter import GATE_IDS
from nexus_sandbox.gate_bound_host import inspect_cortex_module


class Host:
    def __init__(self):
        self.calls = []
        self.identity = {"provider": "CORTEX", "principal": "viewer1",
                         "authenticated": True}
        self.grants = {"provider": "CORTEX", "principal": "viewer1",
                       "target": "synthetic:cp02", "permissions": ["module.view"],
                       "complete": True}
        self.snapshot = {"provider": "CORTEX", "principal": "viewer1",
                         "target": "synthetic:cp02", "revision": "r1",
                         "complete": True, "truncated": False}

    def identity_exact(self):
        self.calls.append("identity")
        return dict(self.identity)

    def permissions_exact(self, target):
        self.calls.append("grants")
        return dict(self.grants)

    def read_exact(self, target):
        self.calls.append("read")
        return dict(self.snapshot)


class CortexBoundReadTests(unittest.TestCase):
    def setUp(self):
        self.host = Host()
        self.op = {"id": "cp02:host:1", "principal": "viewer1",
                   "provider": "CORTEX", "target": "synthetic:cp02",
                   "action": "read", "synthetic": True}
        self.register = {g: "BLOCKED" for g in GATE_IDS}

    def run_case(self, operation=None, evidence=None, gates=("CP02",)):
        return inspect_cortex_module(
            operation=self.op if operation is None else operation,
            checkpoint_statuses=self.register, applicable_gates=gates,
            other_boundary_evidence={} if evidence is None else evidence,
            host=self.host)

    def test_matching_identity_grant_and_read_is_only_host_assertion(self):
        result = self.run_case()
        self.assertEqual(result.status, "READBACK_MATCHED_HOST_ASSERTION")
        self.assertEqual(self.host.calls, ["identity", "grants", "read"])
        self.assertFalse(result.execution_authorized)
        self.assertEqual(result.provider_writes, 0)

    def test_mismatched_principal_holds_before_grants_and_read(self):
        self.host.identity["principal"] = "owner"
        self.assertEqual(self.run_case().status, "HELD")
        self.assertEqual(self.host.calls, ["identity"])

    def test_explicit_authentication_false_holds(self):
        self.host.identity["authenticated"] = False
        self.assertEqual(self.run_case().status, "HELD")
        self.assertEqual(self.host.calls, ["identity"])

    def test_unverified_grant_holds_without_read(self):
        for v in ([], ["issue.view"], ["module.edit"]):
            self.host.calls = []
            self.host.grants["permissions"] = v
            self.assertEqual(self.run_case().status, "HELD")
            self.assertEqual(self.host.calls, ["identity", "grants"])

    def test_grant_target_or_principal_mismatch_holds(self):
        for key, value in (("target", "synthetic:other"),
                           ("principal", "owner"), ("provider", "NOTION")):
            self.host.calls = []
            self.host.grants[key] = value
            self.assertEqual(self.run_case().status, "HELD")
            self.assertEqual(self.host.calls, ["identity", "grants"])
            self.host.grants[key] = self.op[key]

    def test_incomplete_or_malformed_grants_hold(self):
        for value in (False, "true"):
            self.host.calls = []
            self.host.grants["complete"] = value
            self.assertEqual(self.run_case().status, "HELD")
            self.assertEqual(self.host.calls, ["identity", "grants"])

    def test_caller_cannot_forge_cp02_evidence(self):
        result = self.run_case(evidence={"CP02": True})
        self.assertEqual(result.status, "HELD")
        self.assertEqual(self.host.calls, [])

    def test_unverified_other_applicable_gate_stops_read(self):
        result = self.run_case(gates=("CP02", "CP04"))
        self.assertEqual(result.status, "HELD")
        self.assertEqual(result.outstanding, ("CP04",))
        self.assertEqual(self.host.calls, ["identity", "grants"])

    def test_wrong_readback_identity_holds(self):
        self.host.snapshot["principal"] = "owner"
        self.assertEqual(self.run_case().status, "HELD")

    def test_provider_failure_holds_without_read(self):
        self.host.permissions_exact = lambda target: 1 / 0
        self.assertEqual(self.run_case().next_action,
                         "PROVIDER_IDENTITY_OR_GRANTS_ERROR")
        self.assertEqual(self.host.calls, ["identity"])

    def test_writes_and_non_synthetic_are_refused_without_call(self):
        for changes in ({"action": "update"}, {"synthetic": False},
                        {"target": "production:module"}):
            self.host.calls = []
            self.assertEqual(self.run_case(operation={**self.op, **changes}).status,
                             "HELD")
            self.assertEqual(self.host.calls, [])


if __name__ == "__main__":
    unittest.main()
