"""Bounded offline recovery tests for the GitHub/Cortex synthetic bridge."""
import tempfile
import unittest
from pathlib import Path
from nexus_sandbox.cortex_adapter import CortexAdapter, Module, MARKER
from nexus_sandbox.github_cortex_bridge import make_fixture
from nexus_sandbox.github_cortex_event import REPOSITORY

SOURCE = "Nexus Sandbox Recovery Source"
TARGET = "Nexus Sandbox Recovery Target"
KEY = "synthetic:request:Recovery40815901422"


class Transport:
    def __init__(self, source):
        self.data = {source.name: source}
        self.creates = 0
        self.lose_ack = True

    def get(self, name):
        return self.data.get(name)

    def create(self, name, content, dependencies):
        self.creates += 1
        self.data[name] = Module("stable-id", name, 1, content, dependencies)
        if self.lose_ack:
            raise TimeoutError("Simulated lost acknowledgment")

    def update(self, *args):
        raise AssertionError("Unexpected update")


class RecoveryTests(unittest.TestCase):
    def test_lost_ack_restart_reconciles_without_duplicate_write(self):
        source = Module("source-id", SOURCE, 1, MARKER + "\nsource", ())
        transport = Transport(source)
        run = dict(id=40815901422, run_attempt=1, head_sha="14211bfb08fb17d2b5f38867d5664868a4abfdc6",
                   conclusion="success", status="completed", workflow_id=395432308,
                   repository={"full_name": REPOSITORY},
                   html_url=f"https://github.com/{REPOSITORY}/actions/runs/40815901422")
        request = make_fixture(run, source, TARGET, KEY)
        with tempfile.TemporaryDirectory() as folder:
            journal = Path(folder) / "durable.sqlite"
            first = CortexAdapter(journal, frozenset((SOURCE, TARGET)), transport).ensure(request)
            self.assertEqual(first.protocol_verdict, "UNKNOWN")
            self.assertEqual(transport.creates, 1)
            transport.lose_ack = False
            second = CortexAdapter(journal, frozenset((SOURCE, TARGET)), transport).ensure(request)
            self.assertEqual(second.protocol_verdict, "VERIFIED")
            self.assertEqual(transport.creates, 1)
            third = CortexAdapter(journal, frozenset((SOURCE, TARGET)), transport).ensure(request)
            self.assertEqual(third.protocol_verdict, "VERIFIED")
            self.assertEqual(transport.creates, 1)


if __name__ == "__main__":
    unittest.main()
