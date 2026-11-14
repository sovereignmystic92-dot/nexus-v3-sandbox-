"""Exercise actual SQLite persistence with the existing Cortex journal."""

from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from nexus_sandbox.cortex_adapter import MARKER, CortexAdapter, Module, Write
from nexus_sandbox.sqlite_memory_transport import SQLiteMemoryTransport


class InterruptedTransport(SQLiteMemoryTransport):
    def create(self, name, content, dependencies):
        super().create(name, content, dependencies)
        raise SystemExit("interrupted after commit")


class SQLiteMemoryTransportTests(unittest.TestCase):
    def test_update_preserves_identity_and_increments_version(self):
        with tempfile.TemporaryDirectory() as directory:
            transport = SQLiteMemoryTransport(Path(directory) / "modules.sqlite")
            self.assertIsNone(transport.get("output"))
            with self.assertRaises(KeyError):
                transport.update("output", "v1", ())
            transport.create("output", "v1", ("source",))
            original = transport.get("output")
            transport.update("output", "v2", ("source", "another"))
            self.assertEqual(
                transport.get("output"), Module(original.id, "output", 2, "v2", ("source", "another")),
            )
    def test_restart_recovers_committed_write_without_repeating_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport = InterruptedTransport(root / "modules.sqlite")
            journal = root / "journal.sqlite"
            source_name = "Nexus Sandbox Memory Source"
            target = "Nexus Sandbox Memory Output"
            SQLiteMemoryTransport(root / "modules.sqlite").create(
                source_name, MARKER + "\nOriginal ñ\n", (),
            )
            source = transport.get(source_name)
            key = "synthetic:request:local-memory"
            content = f"{MARKER}\n{key}\nExact output ñ\n"
            request = Write(key, target, content, (source_name,), source)
            adapter = CortexAdapter(journal, frozenset((source_name, target)), transport)
            with self.assertRaisesRegex(SystemExit, "interrupted after commit"):
                adapter.ensure(request)
            original = transport.get(target)
            self.assertEqual(original, Module(original.id, target, 1, content, (source_name,)))

            script = """
from dataclasses import asdict
import json
from pathlib import Path
import sys
from nexus_sandbox.cortex_adapter import CortexAdapter, Module, Write
from nexus_sandbox.sqlite_memory_transport import SQLiteMemoryTransport

root = Path(sys.argv[1])
payload = json.loads(sys.argv[2])
payload["dependencies"] = tuple(payload["dependencies"])
payload["source"]["dependencies"] = tuple(payload["source"]["dependencies"])
payload["source"] = Module(**payload["source"])
request = Write(**payload)
transport = SQLiteMemoryTransport(root / "modules.sqlite")
adapter = CortexAdapter(root / "journal.sqlite", frozenset((request.source.name, request.name)), transport)
outcome = adapter.ensure(request)
print(json.dumps([asdict(outcome), asdict(transport.get(request.name)), asdict(transport.get(request.source.name))]))
"""
            result = subprocess.run(
                [sys.executable, "-c", script, directory, json.dumps(asdict(request))],
                check=True, capture_output=True, text=True, timeout=10,
            )
            outcome, readback, source_readback = json.loads(result.stdout)
            self.assertEqual(outcome["protocol_verdict"], "VERIFIED")
            self.assertEqual(outcome["operation_outcome"], "NOT_ATTEMPTED")
            self.assertEqual(outcome["module_id"], original.id)
            self.assertEqual(readback, json.loads(json.dumps(asdict(original))))
            self.assertEqual(source_readback, json.loads(json.dumps(asdict(source))))
