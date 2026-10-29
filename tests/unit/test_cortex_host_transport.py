import tempfile
import unittest
from pathlib import Path

from nexus_sandbox.cortex_adapter import CortexAdapter, MARKER, Module
from nexus_sandbox.cortex_host_transport import CortexHostTransport

SOURCE = "Nexus Sandbox Host Source"
TARGET = "Nexus Sandbox Host Target"
KEY = "synthetic:request:HostRecovery123"


class HostTransportTests(unittest.TestCase):
    def test_strict_mapping_and_read_outage(self):
        transport = CortexHostTransport(read=lambda name: {"id": "id", "name": name, "version": 1, "content": MARKER, "dependencies": []},
                                        create=lambda *args: None, update=lambda *args: None)
        self.assertEqual(transport.get(SOURCE).id, "id")
        broken = CortexHostTransport(read=lambda _: {"id": "id", "name": SOURCE, "version": 1, "content": MARKER, "dependencies": "bad"},
                                     create=lambda *args: None, update=lambda *args: None)
        with self.assertRaises(ValueError):
            broken.get(SOURCE)
        outage = CortexHostTransport(read=lambda _: (_ for _ in ()).throw(ConnectionError("offline")),
                                     create=lambda *args: None, update=lambda *args: None)
        with self.assertRaises(ConnectionError):
            outage.get(SOURCE)

    def test_adapter_host_recovery_after_lost_ack(self):
        source = Module("source-id", SOURCE, 1, MARKER + "\nsource", ())
        remote = {SOURCE: source}
        calls = []
        def read(name):
            module = remote.get(name)
            return None if module is None else dict(id=module.id, name=module.name,
                version=module.version, content=module.content, dependencies=list(module.dependencies))
        def create(name, content, dependencies):
            calls.append(name)
            remote[name] = Module("target-id", name, 1, content, tuple(dependencies))
            raise TimeoutError("write succeeded, response lost")
        host = CortexHostTransport(read=read, create=create, update=lambda *args: None)
        from nexus_sandbox.cortex_adapter import Write
        request = Write(KEY, TARGET, MARKER + "\n" + KEY, (), source)
        with tempfile.TemporaryDirectory() as folder:
            journal = Path(folder) / "journal.sqlite"
            first = CortexAdapter(journal, frozenset((SOURCE, TARGET)), host).ensure(request)
            self.assertEqual(first.protocol_verdict, "UNKNOWN")
            second = CortexAdapter(journal, frozenset((SOURCE, TARGET)), host).ensure(request)
            self.assertEqual(second.protocol_verdict, "VERIFIED")
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
