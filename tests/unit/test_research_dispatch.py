import copy
import unittest

from nexus_sandbox.research_dispatch import dispatch_research
from nexus_sandbox.research_loop import initial_state


class ResearchDispatchTests(unittest.TestCase):
    def setUp(self):
        self.binding = dict(mission_id="pilot", source_revision="v1",
                            policy_revision="p1", code_revision="c1")
        self.state = initial_state(self.binding, [
            dict(id="accuracy", question="What did the studies measure?",
                 scope_reason="Repeated exposure pilot")
        ])
        self.research_calls = 0
        self.read_calls = 0

    def read(self, _mission):
        self.read_calls += 1
        return copy.deepcopy(self.state)

    def save(self, _mission, state):
        self.state = copy.deepcopy(state)

    def assess(self, _question, _state):
        self.research_calls += 1
        return dict(disposition="RESOLVED", reason="Synthetic pilot assessment",
                    attempted_queries=["fixture"], evidence=[], followups=[], connections=[])

    def dispatch(self, trigger, due):
        return dispatch_research(self.binding, self.assess, self.save, self.read,
                                 trigger=trigger, is_due=due)["status"]

    def test_interactive_and_early_schedule_do_not_touch_research(self):
        self.assertEqual(self.dispatch("interactive", True), "DEFERRED_TO_QUEUE")
        self.assertEqual(self.dispatch("schedule", False), "NOT_DUE")
        self.assertEqual(self.read_calls, 0)
        self.assertEqual(self.research_calls, 0)

    def test_manual_and_due_schedule_share_checkpoint_without_replay(self):
        self.assertEqual(self.dispatch("manual", False), "FRONTIER_EXHAUSTED")
        self.assertEqual(self.dispatch("schedule", True), "FRONTIER_EXHAUSTED")
        self.assertEqual(self.research_calls, 1)

    def test_bounded_run_retains_evidence_connections_and_open_questions(self):
        def assess(_question, _state):
            return dict(
                disposition="RESOLVED",
                reason="Controlled studies measured perceived accuracy",
                attempted_queries=["repeated headlines and perceived accuracy"],
                evidence=[dict(id="study", source_ref="doi:10.1037/xge0000465",
                               claim="Prior exposure increased perceived accuracy",
                               classification="OBSERVATION")],
                followups=[
                    dict(id="sharing", question="Does repetition affect actual sharing?",
                         scope_reason="Look for observed sharing in field studies"),
                    dict(id="durability", question="Does the effect persist?",
                         scope_reason="Look for follow-up beyond one week"),
                ],
                connections=[dict(
                    statement="The study provides evidence for the existing perceived accuracy claim",
                    classification="SUPPORTED_RELATION",
                    evidence_ids=["study"],
                    counterexamples=["Perceived accuracy does not measure sharing"],
                )],
            )

        result = dispatch_research(self.binding, assess, self.save, self.read,
                                   trigger="manual", is_due=False, max_steps=1)

        self.assertEqual(result["status"], "PAUSED_BUDGET")
        self.assertEqual(result["state"], self.state)
        self.assertEqual(set(self.state["findings"]), {"accuracy"})
        self.assertEqual([q["id"] for q in self.state["questions"]], [
            "accuracy", "sharing", "durability",
        ])
        self.assertEqual(len(self.state["connections"]), 1)
        self.assertEqual(self.state["connections"][0]["evidence_ids"], ["study"])

    def test_unknown_trigger_fails_before_running_callbacks(self):
        with self.assertRaises(ValueError):
            self.dispatch("unknown", True)
        self.assertEqual(self.read_calls, 0)
        self.assertEqual(self.research_calls, 0)
