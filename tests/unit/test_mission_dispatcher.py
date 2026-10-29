"""Synthetic dispatcher decisions: no live callbacks, polling or writes."""
import unittest

from nexus_sandbox.mission_dispatcher import Mission, dispatch


class MissionDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.mission = Mission("synthetic-01", "PASSIVE", "new-research-item",
                               ("source-ready", "scope-approved"),
                               ("inspect-source", "collect-evidence", "verify-report"))

    def decide(self, **kwargs):
        defaults = dict(observed_triggers=("new-research-item",),
                        satisfied_dependencies=("source-ready", "scope-approved"))
        defaults.update(kwargs)
        return dispatch(self.mission, **defaults)

    def test_missing_trigger_holds(self):
        r = self.decide(observed_triggers=())
        self.assertEqual((r["state"], r["reason"]), ("HOLD", "TRIGGER_NOT_OBSERVED"))

    def test_dependencies_are_ordered_and_fail_closed(self):
        r = self.decide(satisfied_dependencies=("source-ready",))
        self.assertEqual(r["state"], "HOLD")
        self.assertEqual(r["next_action"], "Verify dependency: scope-approved")

    def test_ready_advances_only_on_verified_readback(self):
        r = self.decide()
        self.assertEqual(r["state"], "READY")
        self.assertIn("inspect-source", r["next_action"])
        r2 = self.decide(verified_steps=("inspect-source",))
        self.assertIn("collect-evidence", r2["next_action"])
        self.assertEqual(self.decide(verified_steps=self.mission.steps)["state"], "COMPLETE")

    def test_blocked_step_holds_even_if_other_steps_verified(self):
        r = self.decide(verified_steps=("inspect-source",),
                        blocked_steps=("collect-evidence",))
        self.assertEqual(r["reason"], "STEP_BLOCKED")

    def test_active_requires_bound_authorization(self):
        active = Mission("active-01", "ACTIVE", "user-request", (),
                         ("bounded-inspection",))
        r = dispatch(active, observed_triggers=("user-request",))
        self.assertEqual(r["reason"], "ACTIVE_AUTHORIZATION_REQUIRED")
        authorized = dispatch(active, observed_triggers=("user-request",),
                              authorized_active=True)
        self.assertEqual(authorized["state"], "READY")

    def test_repeated_input_is_deterministic(self):
        self.assertEqual(self.decide(), self.decide())

    def test_out_of_scope_or_conflicting_evidence_rejected(self):
        with self.assertRaises(ValueError):
            self.decide(verified_steps=("unknown",))
        with self.assertRaises(ValueError):
            self.decide(verified_steps=("inspect-source",),
                        blocked_steps=("inspect-source",))
        with self.assertRaises(ValueError):
            self.decide(satisfied_dependencies=("invented",))

    def test_bound_and_duplicate_steps_rejected(self):
        with self.assertRaises(ValueError):
            dispatch(Mission("m", "PASSIVE", "t", (), ("x", "y"), 1))
        with self.assertRaises(ValueError):
            dispatch(Mission("m", "PASSIVE", "t", (), ("x", "x")))

    def test_unknown_trigger_cannot_activate(self):
        r = self.decide(observed_triggers=("other-trigger",))
        self.assertEqual(r["state"], "HOLD")
        self.assertEqual(r["reason"], "TRIGGER_NOT_OBSERVED")

    def test_decision_has_no_execution_authority(self):
        r = self.decide()
        self.assertEqual(r["authority"], "NON_EXECUTING_DECISION")


if __name__ == "__main__":
    unittest.main()
