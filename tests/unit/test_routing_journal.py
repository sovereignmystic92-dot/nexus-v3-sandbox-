"""Synthetic SQLite routing persistence; no real provider calls."""
import tempfile
from pathlib import Path
import unittest

from nexus_sandbox.agent_routing import AgentCapability
from nexus_sandbox.mission_dispatcher import Mission
from nexus_sandbox.mission_journal import MissionJournal
from nexus_sandbox.routing_journal import (
    provision_routing_records, record_routing_proposal, observe_routing_proposal,
)


class RoutingJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "missions.sqlite"
        self.journal = MissionJournal.provision(self.file, "synthetic-routing-only")
        self.mission = Mission("mission-assign", "PASSIVE", "owner", (), ("draft", "review"))
        self.roster = (
            AgentCapability("Gemini", ("analysis", "research"), True, True),
            AgentCapability("ChatGPT", ("analysis",), True, True),
        )
        provision_routing_records(self.journal)
        self.journal.record(self.mission, observed_triggers=("owner",))
        self.kw = dict(required_skills=("analysis",), agents=self.roster, expected_revision=1)

    def save(self, **kwargs):
        data = dict(self.kw)
        data.update(kwargs)
        return record_routing_proposal(self.journal, self.mission, **data)

    def test_replay_and_separate_agents(self):
        record = self.save()
        self.assertEqual(record["routing"]["state"], "READY")
        self.assertEqual((record["routing"]["lead"], record["routing"]["reviewer"]),
                         ("Gemini", "ChatGPT"))
        self.assertEqual(self.save(), record)
        self.assertEqual(observe_routing_proposal(self.journal, "mission-assign", 1),
                         record)

    def test_reopened_journal_has_same_record(self):
        first = self.save()
        reopened = MissionJournal(self.file, "synthetic-routing-only")
        self.assertEqual(observe_routing_proposal(reopened, self.mission.mission_id, 1),
                         first)

    def test_same_revision_changed_roster_holds(self):
        self.save()
        new_roster = (self.roster[0],
                      AgentCapability("ChatGPT", ("analysis", "extra"), True, True))
        with self.assertRaisesRegex(ValueError, "Conflicting routing"):
            self.save(agents=new_roster)

    def test_unapproved_reviewer_holds(self):
        roster = (self.roster[0],
                  AgentCapability("ChatGPT", ("analysis",), True, False))
        self.assertEqual(self.save(agents=roster)["routing"]["reason"],
                         "NO_DISTINCT_QUALIFIED_REVIEWER")

    def test_existing_hold_not_promoted_to_ready(self):
        other = Mission("held", "PASSIVE", "missing", (), ("draft",))
        self.journal.record(other)
        record = record_routing_proposal(
            self.journal, other, required_skills=("analysis",),
            agents=self.roster, expected_revision=1)
        self.assertEqual(record["routing"]["state"], "HOLD")

    def test_stale_revision_fails(self):
        with self.assertRaisesRegex(ValueError, "Stale or missing"):
            self.save(expected_revision=2)

    def test_missing_original_journal_never_replaced(self):
        self.file.unlink()
        with self.assertRaises(FileNotFoundError):
            self.save()
        self.assertFalse(self.file.exists())

    def test_missing_explicit_schema_holds(self):
        otherdir = Path(self.tmp.name) / "other"
        otherdir.mkdir(mode=0o700)
        other = MissionJournal.provision(otherdir / "j.sqlite", "other")
        other.record(self.mission, observed_triggers=("owner",))
        with self.assertRaisesRegex(ValueError, "not provisioned"):
            record_routing_proposal(other, self.mission, **self.kw)

    def test_routing_record_immutable_after_other_evidence_revision(self):
        initial = self.save()
        self.journal.record(self.mission, observed_triggers=("owner",),
                            verified_steps=("draft",), expected_revision=1)
        with self.assertRaisesRegex(ValueError, "Stale or missing"):
            self.save(expected_revision=1)
        self.assertEqual(observe_routing_proposal(self.journal, "mission-assign", 1),
                         initial)
        second = self.save(expected_revision=2)
        self.assertEqual(second["revision"], 2)
        self.assertEqual(second["routing"]["next_action"],
                         "Execute bounded step and independently verify: review")


if __name__ == "__main__":
    unittest.main()
