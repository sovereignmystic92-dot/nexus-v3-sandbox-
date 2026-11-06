import tempfile
import unittest
from pathlib import Path
from nexus_sandbox.cortex_host_bound_handoff import execute_host_bound_handoff
from nexus_sandbox.cortex_host_binding import HostBindingBlocked
from nexus_sandbox.cortex_handoff_journal import HandoffJournal, Intent, analysis_hash

SRC = "https://app.notion.com/p/source123"
OUT = "https://app.notion.com/p/analysis456"
INTENT = Intent("tx", SRC, OUT, "rev1", "rev2", "account", "owner", analysis_hash("report"))
BASE = dict(intent=INTENT, analysis_text="report",
            source_page_id="source123", analysis_page_id="analysis456",
            observed_account="account", observed_owner="owner",
            registry_pages=[{"digest": "a"*64}], registry_complete=True,
            source_verified=True, analysis_verified=True,
            exclusive_worker=True, durable_journal=True,
            modules=[], authorized_write=False)

class HostBoundHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal = HandoffJournal(Path(self.tmp.name) / "handoff.sqlite")

    def call(self, **overrides):
        return execute_host_bound_handoff(
            journal=self.journal, **{**BASE, **overrides},
            create_module=lambda *_: self.fail("unauthorized create"),
            fetch_module=lambda _: self.fail("unexpected read"))

    def test_wrong_account_fails_before_journal(self):
        with self.assertRaises(HostBindingBlocked):
            self.call(observed_account="wrong")
        self.assertEqual(self.journal.begin(INTENT)[0], "PREPARED")

    def test_wrong_source_page_fails_before_journal(self):
        with self.assertRaises(HostBindingBlocked):
            self.call(source_page_id="unrelated")

    def test_missing_worker_fails_before_journal(self):
        with self.assertRaises(HostBindingBlocked):
            self.call(exclusive_worker=False)

    def test_incomplete_registry_fails_before_journal(self):
        with self.assertRaises(HostBindingBlocked):
            self.call(registry_complete=False)

if __name__ == "__main__":
    unittest.main()
