import tempfile
import unittest
from pathlib import Path
from nexus_sandbox.cortex_handoff_journal import HandoffJournal, Intent, JournalHold, analysis_hash
from nexus_sandbox.cortex_journaled_handoff import execute_journaled_handoff
from nexus_sandbox.cortex_handoff_preflight import HandoffBlocked

SOURCE = "https://app.notion.com/p/source"
ANALYSIS = "https://app.notion.com/p/analysis"
TEXT = "derived report"
INTENT = Intent("tx1", SOURCE, ANALYSIS, "source-rev", "analysis-rev",
                "account", "owner", analysis_hash(TEXT))
BASE = dict(intent=INTENT, analysis_text=TEXT, modules=[],
            destination_confirmed=True, registry_complete=True,
            authorized_write=True, exclusive_worker=True)

class JournalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal = HandoffJournal(Path(self.tmp.name) / "j.sqlite")

    def run_handoff(self, **kw):
        return execute_journaled_handoff(journal=self.journal, **{**BASE, **kw})

    def test_write_intent_precedes_create_and_survives_uncertainty(self):
        def create(*_):
            self.assertEqual(self.journal.begin(INTENT)[0], "WRITE_INTENT")
            raise TimeoutError("ambiguous")
        with self.assertRaises(Exception):
            self.run_handoff(create_module=create, fetch_module=lambda _: None)
        self.assertEqual(self.journal.begin(INTENT)[0], "WRITE_INTENT")
        with self.assertRaises(JournalHold):
            self.run_handoff(create_module=lambda *_: self.fail("duplicate"),
                             fetch_module=lambda _: None)

    def test_missing_worker_blocks_before_intent(self):
        with self.assertRaises(JournalHold):
            self.run_handoff(exclusive_worker=False, create_module=lambda *_: None,
                             fetch_module=lambda _: None)
        self.assertEqual(self.journal.begin(INTENT)[0], "PREPARED")

    def test_no_authorization_does_not_issue_intent(self):
        with self.assertRaises(HandoffBlocked):
            self.run_handoff(authorized_write=False, create_module=lambda *_: None,
                             fetch_module=lambda _: None)
        self.assertEqual(self.journal.begin(INTENT)[0], "PREPARED")

    def test_changed_analysis_is_blocked(self):
        with self.assertRaises(JournalHold):
            self.run_handoff(analysis_text="changed", create_module=lambda *_: None,
                             fetch_module=lambda _: None)

if __name__ == "__main__":
    unittest.main()
