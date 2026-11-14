"""Offline Dot adapter tests; no actual Dot connection is invoked."""
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load("dot_nexus_adapter", "tools/dot_nexus_adapter.py")
runner = load("module_evolution_runner", "tools/module_evolution_runner.py")


def proposal(**changes):
    value = {
        "schema_version": "dot_nexus_event_v1",
        "event_id": "finding-1",
        "origin": {"kind": "dot", "agent_id": "research"},
        "observed_at": "2026-11-14T12:00:00Z",
        "module_hints": ["skill_forge", "civilization_engine"],
        "subject": "Untrusted research finding",
        "source_refs": [{"uri": "https://example.org/study", "sha256": None}],
        "proposed_action": "review",
        "evidence_status": "UNVERIFIED",
        "idempotency_key": "research-1",
    }
    value.update(changes)
    return value


class DotAdapterTests(unittest.TestCase):
    def test_all_five_modules_and_offline_receipt(self):
        item = proposal(module_hints=list(adapter.MODULES))
        envelope = adapter.normalize(item)
        self.assertEqual(envelope["module_hints"], sorted(adapter.MODULES))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.sqlite"
            a = runner.evaluate(path, envelope)
            b = runner.evaluate(path, adapter.normalize(item))
            self.assertEqual(a, b)
            self.assertEqual(a["status"], "PENDING_VALIDATION")
            self.assertFalse(a["readiness_advanced"])
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM event_receipts").fetchone()[0], 1)

    def test_rejects_invalid_proposals(self):
        bad = [
            proposal(module_hints=["root_access"]),
            proposal(module_hints=[]),
            proposal(proposed_action="execute"),
            proposal(evidence_status="VERIFIED"),
            proposal(origin={"kind": "dot", "agent_id": ""}),
            proposal(observed_at="2026-11-14"),
            proposal(source_refs=[]),
            proposal(source_refs=[{"uri": "http://example.org", "sha256": None}]),
            proposal(source_refs=[{"uri": "https://example.org", "sha256": "no"}]),
            proposal(schema_version="unknown"),
            proposal(subject="x" * 40000),
        ]
        for item in bad:
            with self.subTest(item=item.get("proposed_action"), source=item.get("source_refs")):
                with self.assertRaises(ValueError):
                    adapter.normalize(item)

    def test_proposal_does_not_advance_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = runner.evaluate(Path(tmp) / "events.sqlite", adapter.normalize(proposal()))
            self.assertEqual(receipt["evidence_class"], "offline")
            self.assertFalse(receipt["readiness_advanced"])


if __name__ == "__main__":
    unittest.main()
