"""Safety regressions for provider-free gate-bound operation assessment."""
import unittest

from nexus_sandbox.gate_bound_adapter import assess_operation, GATE_IDS


class GateBoundAdapterTests(unittest.TestCase):
    def setUp(self):
        self.op = {"id": "synthetic-01", "principal": "viewer",
                   "provider": "CORTEX", "target": "synthetic:module",
                   "action": "read", "synthetic": True}
        self.register = {gate: "PASSED" for gate in GATE_IDS}

    def decide(self, gates=("CP02",), evidence=None, op=None, register=None):
        return assess_operation(
            operation=self.op if op is None else op,
            checkpoint_statuses=self.register if register is None else register,
            applicable_gates=gates,
            boundary_evidence={} if evidence is None else evidence)

    def test_no_read_without_runtime_proof_even_if_checkpoints_passed(self):
        d = self.decide()
        self.assertEqual(d.status, "HOLD")
        self.assertEqual(d.outstanding, ("CP02",))

    def test_read_is_eligible_but_not_executed(self):
        d = self.decide(evidence={"CP02": True})
        self.assertEqual(d.status, "READ_ONLY_ELIGIBLE")
        self.assertFalse(d.execution_authorized)
        self.assertEqual(d.provider_writes, 0)

    def test_false_or_partial_proof_holds(self):
        for ev in ({"CP02": False}, {}, {"CP02": True, "CP03": False}):
            d = self.decide(gates=("CP02", "CP03"),
                            evidence=ev)
            self.assertEqual(d.status, "HOLD")

    def test_a_verified_viewer_role_does_not_allow_write(self):
        op = dict(self.op, action="update")
        d = self.decide(op=op, evidence={"CP02": True})
        self.assertEqual(d.status, "HOLD")
        self.assertEqual(d.next_action, "REQUIRE_INSTALLED_PROVIDER_WRITE_GUARD")
        self.assertFalse(d.execution_authorized)

    def test_production_write_always_held(self):
        d = self.decide(op=dict(self.op, action="create", synthetic=False),
                        evidence={"CP02": True})
        self.assertEqual(d.next_action, "PRODUCTION_WRITE_NOT_AUTHORIZED")

    def test_no_escalation_or_provider_dispatch(self):
        for action in ("permissions", "delete", "dispatch"):
            d = self.decide(op=dict(self.op, action=action),
                            evidence={"CP02": True})
            self.assertEqual(d.status, "HOLD")

    def test_missing_register_entries_rejected(self):
        bad = dict(self.register)
        bad.pop("CP09")
        self.assertEqual(self.decide(register=bad).status, "HOLD")

    def test_unscoped_evidence_rejected(self):
        self.assertEqual(self.decide(evidence={"CP09": True}).status, "HOLD")

    def test_string_as_boolean_evidence_rejected(self):
        self.assertEqual(self.decide(evidence={"CP02": "true"}).status, "HOLD")

    def test_unrecognized_provider_rejected(self):
        self.assertEqual(self.decide(op=dict(self.op, provider="OWNER")).status, "HOLD")

    def test_empty_scope_rejected(self):
        self.assertEqual(self.decide(gates=(), evidence={}).status, "HOLD")

    def test_unrecognized_action_rejected(self):
        self.assertEqual(self.decide(op=dict(self.op, action="merge")).status, "HOLD")


if __name__ == "__main__":
    unittest.main()
