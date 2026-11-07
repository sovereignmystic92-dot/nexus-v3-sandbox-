import json
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.nexus_gateway_runtime import execute
from nexus_sandbox.transcript_live_handoff import Observed


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.notion = {}
        self.cortex = {}
        self.ports = {
            "notion_read": lambda k: Observed(k, self.notion[k]) if k in self.notion else None,
            "notion_write": lambda k, v: self.notion.__setitem__(k, v),
            "cortex_read": lambda k: Observed(k, self.cortex[k]) if k in self.cortex else None,
            "cortex_write": lambda k, v: self.cortex.__setitem__(k, v),
        }
        self.job = dict(mode="manual", source_url="https://youtu.be/_p6lrFsVPzQ",
                        transcript="Full source.", notion_page_id="notion-1",
                        cortex_module_name="module-1", analysis="Analysis.",
                        grants=dict(process=True, notion_write=True, cortex_write=True))

    def test_receipt_never_attests_host(self):
        result = execute(run_id="test-1", receipt_dir=self.tmp.name,
                         provider_ports=self.ports, **self.job)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["gateway_status"], "READBACK_MATCHED")
        self.assertFalse(result["provider_identity_attested"])
        self.assertFalse(result["audit_gate_promoted"])
        stored = json.loads((Path(self.tmp.name) / "test-1.json").read_text())
        self.assertEqual(stored, result)

    def test_duplicate_run_refuses_overwrite(self):
        execute(run_id="test-2", receipt_dir=self.tmp.name,
                provider_ports=self.ports, **self.job)
        with self.assertRaises(FileExistsError):
            execute(run_id="test-2", receipt_dir=self.tmp.name,
                    provider_ports=self.ports, **self.job)

    def test_denied_processing_records_incomplete(self):
        self.job["grants"]["process"] = False
        result = execute(run_id="test-3", receipt_dir=self.tmp.name,
                         provider_ports=self.ports, **self.job)
        self.assertEqual(result["gateway_status"], "BLOCKED")
        self.assertFalse(self.notion)
        self.assertFalse(self.cortex)

    def test_uncertain_provider_error_preserves_marker(self):
        def fail(_key):
            raise RuntimeError("provider unavailable")
        self.ports["notion_read"] = fail
        with self.assertRaises(RuntimeError):
            execute(run_id="test-5", receipt_dir=self.tmp.name,
                    provider_ports=self.ports, **self.job)
        marker = json.loads((Path(self.tmp.name) / "test-5.json").read_text())
        self.assertEqual(marker["next_action"], "RECONCILE_UNCERTAIN_RUN")
        with self.assertRaises(FileExistsError):
            execute(run_id="test-5", receipt_dir=self.tmp.name,
                    provider_ports=self.ports, **self.job)

    def test_missing_port_rejected(self):
        with self.assertRaises(ValueError):
            execute(run_id="test-4", receipt_dir=self.tmp.name,
                    provider_ports={}, **self.job)


if __name__ == "__main__":
    unittest.main()
