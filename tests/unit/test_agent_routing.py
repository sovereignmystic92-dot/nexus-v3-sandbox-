"""Synthetic routing proposals: no provider calls or side effects."""
import unittest

from nexus_sandbox.mission_dispatcher import Mission
from nexus_sandbox.agent_routing import AgentCapability, route_mission


class AgentRoutingTests(unittest.TestCase):
    def setUp(self):
        self.mission = Mission("route-001", "PASSIVE", "owner-request", (),
                               ("draft", "review"))
        self.roster = (
            AgentCapability("Gemini", ("analysis", "research", "comparison"), True, True),
            AgentCapability("ChatGPT", ("analysis", "research"), True, True),
        )
        self.kw = dict(required_skills=("analysis",), agents=self.roster,
                       observed_triggers=("owner-request",))

    def route(self, **updates):
        params = dict(self.kw)
        params.update(updates)
        return route_mission(self.mission, **params)

    def test_deterministic_lead_and_separate_reviewer(self):
        first = self.route()
        self.assertEqual((first["lead"], first["reviewer"]), ("Gemini", "ChatGPT"))
        self.assertEqual(first["state"], "READY")
        self.assertEqual(first["external_calls"], 0)
        self.assertEqual(first, self.route(agents=tuple(reversed(self.roster))))

    def test_missing_trigger_holds(self):
        result = self.route(observed_triggers=())
        self.assertEqual(result["state"], "HOLD")
        self.assertIsNone(result["lead"])

    def test_unavailable_agent_not_assigned(self):
        unavailable = (self.roster[0], AgentCapability("ChatGPT", ("analysis",), False, True))
        result = self.route(agents=unavailable)
        self.assertEqual(result["reason"], "NO_DISTINCT_QUALIFIED_REVIEWER")

    def test_unapproved_agent_not_assigned(self):
        unapproved = (AgentCapability("Gemini", ("analysis",), True, False),
                      self.roster[1])
        result = self.route(agents=unapproved)
        self.assertEqual(result["state"], "HOLD")

    def test_no_qualified_lead_holds(self):
        self.assertEqual(self.route(required_skills=("unavailable-skill",))["reason"],
                         "NO_APPROVED_QUALIFIED_LEAD")

    def test_active_mode_requires_authorization(self):
        self.mission = Mission("active-001", "ACTIVE", "owner-request", (), ("draft",))
        result = self.route()
        self.assertEqual(result["reason"], "ACTIVE_AUTHORIZATION_REQUIRED")
        self.assertEqual(result["state"], "HOLD")

    def test_missing_dependency_stops_before_assignment(self):
        self.mission = Mission("deps-001", "PASSIVE", "owner-request", ("source",),
                               ("draft",))
        result = self.route()
        self.assertEqual(result["reason"], "DEPENDENCIES_UNMET")

    def test_invalid_duplicate_agent_rejected(self):
        with self.assertRaises(ValueError):
            self.route(agents=(self.roster[0], self.roster[0]))

    def test_routing_digest_changes_when_roster_changes(self):
        old = self.route()
        changed = self.route(agents=(self.roster[0],
                            AgentCapability("ChatGPT", ("analysis", "extra"), True, True)))
        self.assertNotEqual(old["routing_digest"], changed["routing_digest"])

    def test_completed_dispatch_does_not_assign_new_work(self):
        result = self.route(verified_steps=("draft", "review"))
        self.assertEqual(result["state"], "COMPLETE")
        self.assertIsNone(result["lead"])


if __name__ == "__main__":
    unittest.main()
