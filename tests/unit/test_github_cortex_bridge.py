import tempfile
import unittest
from pathlib import Path

from nexus_sandbox.cortex_adapter import CortexAdapter, Module, MARKER
from nexus_sandbox.github_cortex_bridge import make_fixture
from nexus_sandbox.github_cortex_event import REPOSITORY

SOURCE = "Nexus Sandbox GitHub Source"
TARGET = "Nexus Sandbox GitHub Run Receipt"
KEY = "synthetic:request:GithubRun123"


def sample_run():
    return dict(
        id=123, run_attempt=1, head_sha="a" * 40,
        conclusion="success", status="completed", workflow_id=55,
        repository={"full_name": REPOSITORY},
        html_url=f"https://github.com/{REPOSITORY}/actions/runs/123",
    )


class FakeTransport:
    def __init__(self, source):
        self.modules = {source.name: source}
        self.creates = 0

    def get(self, name):
        return self.modules.get(name)

    def create(self, name, content, dependencies):
        self.creates += 1
        self.modules[name] = Module("target-1", name, 1, content, dependencies)

    def update(self, name, content, dependencies):
        raise AssertionError("Unexpected update")


class BridgeTests(unittest.TestCase):
    def test_create_readback_restart_and_reprocessing(self):
        source = Module("source-1", SOURCE, 1, MARKER + "\nsource", ())
        transport = FakeTransport(source)
        request = make_fixture(sample_run(), source, TARGET, KEY)
        allowed = frozenset((SOURCE, TARGET))
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "receipts.sqlite"
            first = CortexAdapter(journal, allowed, transport).ensure(request)
            self.assertEqual(first.protocol_verdict, "VERIFIED")
            self.assertEqual(transport.creates, 1)
            restarted = CortexAdapter(journal, allowed, transport).ensure(request)
            self.assertEqual(restarted.protocol_verdict, "VERIFIED")
            self.assertEqual(transport.creates, 1)

    def test_conflicting_reuse_is_rejected(self):
        source = Module("source-1", SOURCE, 1, MARKER + "\nsource", ())
        transport = FakeTransport(source)
        allowed = frozenset((SOURCE, TARGET))
        with tempfile.TemporaryDirectory() as directory:
            adapter = CortexAdapter(Path(directory) / "receipts.sqlite", allowed, transport)
            adapter.ensure(make_fixture(sample_run(), source, TARGET, KEY))
            changed = sample_run()
            changed["conclusion"] = "failure"
            with self.assertRaises(ValueError):
                adapter.ensure(make_fixture(changed, source, TARGET, KEY))


if __name__ == "__main__":
    unittest.main()
