"""Offline synthetic Cortex adapter failures, checkpoints and replay."""

from dataclasses import asdict, replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nexus_sandbox.cortex_adapter import BindingConflict, CortexAdapter, MARKER, Module, Write
from nexus_sandbox.cortex_tools import CortexToolTransport, ToolFailure

SOURCE = "Nexus Sandbox Offline Source"
TARGET = "Nexus Sandbox Offline Archive"
OUTPUT = "Nexus Sandbox Offline Output"
REGISTRY = "Nexus Sandbox Offline Registry"
NAMES = frozenset((SOURCE, TARGET, OUTPUT, REGISTRY))


class FakeCortex:
    def __init__(self, source):
        self.modules = {source.name: source}
        self.writes = 0
        self.read_fail = False
        self.lose_reply = False
        self.crash = False
        self.hide = False
        self.corrupt = False
        self.read_calls = []

    def get(self, name):
        self.read_calls.append(name)
        if self.read_fail:
            raise TimeoutError("synthetic read outage")
        return None if self.hide and name != SOURCE else self.modules.get(name)

    def create(self, name, content, dependencies):
        self.writes += 1
        if name in self.modules:
            raise ValueError("synthetic duplicate name")
        self.modules[name] = Module("synthetic:module:" + str(len(self.modules)), name, 1,
                                    "mismatch" if self.corrupt else content, dependencies)
        if self.crash:
            raise SystemExit("synthetic stop after remote commit")
        if self.lose_reply:
            raise TimeoutError("synthetic acknowledgment loss")

    def update(self, name, content, dependencies):
        self.writes += 1
        old = self.modules[name]
        self.modules[name] = replace(old, version=old.version + 1, content=content, dependencies=dependencies)
        if self.lose_reply:
            raise TimeoutError("synthetic acknowledgment loss")


class CortexAdapterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="cortex-adapter-offline-")
        self.addCleanup(temporary.cleanup)
        self.journal = Path(temporary.name) / "cortex.sqlite"
        self.source = Module("synthetic:module:source", SOURCE, 2, MARKER + "\nFictional source v2.", ())
        self.transport = FakeCortex(self.source)
        self.key = "synthetic:request:cortex-offline"
        self.request = Write(self.key, TARGET, MARKER + "\n" + self.key + "\nFictional output", (SOURCE,), self.source)

    def adapter(self):
        return CortexAdapter(self.journal, NAMES, self.transport)

    def test_create_readback_and_restart_retry_have_separate_outcomes(self):
        first = self.adapter().ensure(self.request)
        repeat = self.adapter().ensure(self.request)
        self.assertEqual((first.operation_outcome, first.protocol_verdict), ("SUCCEEDED", "VERIFIED"))
        self.assertEqual((repeat.operation_outcome, repeat.protocol_verdict), ("NOT_ATTEMPTED", "VERIFIED"))
        self.assertEqual((first.module_id, first.module_version), (repeat.module_id, repeat.module_version))
        self.assertEqual(self.transport.writes, 1)

    def test_changed_request_binding_rejected_before_transport_call(self):
        self.adapter().ensure(self.request)
        before = len(self.transport.read_calls)
        with self.assertRaises(BindingConflict):
            self.adapter().ensure(replace(self.request, content=self.request.content + "changed"))
        self.assertEqual(len(self.transport.read_calls), before)
        self.assertEqual(self.transport.writes, 1)

    def test_allowlist_checks_include_dependencies_and_source(self):
        for changes in ({"name": "Production"}, {"dependencies": ("Production",)},
                        {"source": replace(self.source, name="Production")}, {"key": "real-key"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.adapter().ensure(replace(self.request, **changes))
        self.assertEqual((self.transport.writes, self.transport.read_calls), (0, []))

    def test_source_missing_or_changed_holds_without_write(self):
        for source in (None, replace(self.source, version=3), replace(self.source, content=MARKER + " changed")):
            if source is None:
                self.transport.modules.pop(SOURCE, None)
            else:
                self.transport.modules[SOURCE] = source
            self.assertEqual(self.adapter().ensure(self.request).checkpoint, "SOURCE_CHANGED")
        self.assertEqual(self.transport.writes, 0)

    def test_read_timeout_does_not_count_as_absence(self):
        self.transport.read_fail = True
        result = self.adapter().ensure(self.request)
        self.assertEqual((result.operation_outcome, result.protocol_verdict), ("NOT_ATTEMPTED", "UNKNOWN"))
        self.assertEqual(self.transport.writes, 0)

    def test_existing_conflicting_module_is_preserved(self):
        old = Module("synthetic:existing", TARGET, 1, MARKER + " foreign fixture", ())
        self.transport.modules[TARGET] = old
        self.assertEqual(self.adapter().ensure(self.request).checkpoint, "TARGET_CONFLICT")
        self.assertEqual(self.transport.modules[TARGET], old)
        self.assertEqual(self.transport.writes, 0)

    def test_lost_create_response_reconciles_without_duplicate(self):
        self.transport.lose_reply = True
        self.assertEqual(self.adapter().ensure(self.request).protocol_verdict, "UNKNOWN")
        self.assertEqual(self.adapter().ensure(self.request).protocol_verdict, "VERIFIED")
        self.assertEqual(self.transport.writes, 1)

    def test_absence_after_uncertain_create_never_repeats_write(self):
        self.transport.lose_reply = True
        self.adapter().ensure(self.request)
        self.transport.hide = True
        for _ in range(2):
            self.assertEqual(self.adapter().ensure(self.request).checkpoint, "RECONCILE_ONLY")
        self.assertEqual(self.transport.writes, 1)

    def test_process_stop_leaves_durable_intent_then_reconciles(self):
        self.transport.crash = True
        with self.assertRaises(SystemExit):
            self.adapter().ensure(self.request)
        with sqlite3.connect(self.journal) as db:
            row = db.execute("SELECT intent_sent,receipt FROM cortex_receipts").fetchone()
            self.assertEqual(row[0], 1)
            self.assertEqual(json.loads(row[1])["checkpoint"], "WRITE_INTENT")
        self.assertEqual(self.adapter().ensure(self.request).protocol_verdict, "VERIFIED")
        self.assertEqual(self.transport.writes, 1)

    def test_mismatched_write_is_not_verified_or_repaired_automatically(self):
        self.transport.corrupt = True
        result = self.adapter().ensure(self.request)
        self.assertEqual((result.operation_outcome, result.protocol_verdict), ("SUCCEEDED", "FAILED"))
        self.adapter().ensure(self.request)
        self.assertEqual(self.transport.modules[TARGET].content, "mismatch")
        self.assertEqual(self.transport.writes, 1)

    def test_exact_update_baseline_and_retry_preserve_identity(self):
        self.adapter().ensure(self.request)
        old = self.transport.modules[TARGET]
        key = "synthetic:request:cortex-update"
        update = replace(self.request, key=key, content=MARKER + "\n" + key + "\nUpdated payload", before=old)
        first = self.adapter().ensure(update)
        second = self.adapter().ensure(update)
        self.assertEqual((first.protocol_verdict, second.protocol_verdict), ("VERIFIED", "VERIFIED"))
        self.assertEqual((second.module_id, second.module_version), (old.id, old.version + 1))
        self.assertEqual(self.transport.writes, 2)

    def test_stale_update_baseline_blocks_before_write(self):
        self.adapter().ensure(self.request)
        old = self.transport.modules[TARGET]
        self.transport.modules[TARGET] = replace(old, version=2, content=MARKER + " newer state")
        key = "synthetic:request:cortex-stale"
        stale = replace(self.request, key=key, content=MARKER + key + " stale", before=old)
        self.assertEqual(self.adapter().ensure(stale).checkpoint, "TARGET_CONFLICT")
        self.assertEqual(self.transport.writes, 1)

    def test_three_stage_mission_reopens_journal_and_reuses_archive(self):
        plans = ((TARGET, (SOURCE,)), (OUTPUT, (TARGET,)), (REGISTRY, (OUTPUT,)))
        for index, (name, dependencies) in enumerate(plans):
            key = "synthetic:request:stage-" + str(index)
            request = Write(key, name, MARKER + "\n" + key + "\nFictional mission", dependencies, self.source)
            self.assertEqual(self.adapter().ensure(request).protocol_verdict, "VERIFIED")
            self.assertEqual(self.adapter().ensure(request).operation_outcome, "NOT_ATTEMPTED")
        self.assertEqual(self.transport.writes, 3)
        with sqlite3.connect(self.journal) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM cortex_receipts").fetchone()[0], 3)

    def test_failed_journal_transaction_prevents_external_write(self):
        self.adapter()
        with sqlite3.connect(self.journal) as db:
            db.execute("CREATE TRIGGER deny_event BEFORE INSERT ON cortex_events BEGIN SELECT RAISE(ABORT,'synthetic'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.adapter().ensure(self.request)
        self.assertEqual(self.transport.writes, 0)

    def test_source_change_during_write_withholds_completion(self):
        create = self.transport.create
        def change_source(*args):
            create(*args)
            self.transport.modules[SOURCE] = replace(self.source, version=3)
        self.transport.create = change_source
        result = self.adapter().ensure(self.request)
        self.assertEqual((result.operation_outcome, result.protocol_verdict, result.checkpoint),
                         ("SUCCEEDED", "BLOCKED", "SOURCE_CHANGED"))
        self.assertEqual(self.transport.writes, 1)

    def test_readback_outage_recovers_by_read_without_second_write(self):
        create = self.transport.create
        def block_readback(*args):
            create(*args)
            self.transport.read_fail = True
        self.transport.create = block_readback
        result = self.adapter().ensure(self.request)
        self.assertEqual((result.operation_outcome, result.protocol_verdict, result.checkpoint),
                         ("SUCCEEDED", "UNKNOWN", "READBACK_PENDING"))
        self.transport.read_fail = False
        self.assertEqual(self.adapter().ensure(self.request).protocol_verdict, "VERIFIED")
        self.assertEqual(self.transport.writes, 1)


class CortexToolBridgeTests(unittest.TestCase):
    def result(self):
        return {"id": "synthetic:module:1", "name": TARGET, "version": 1,
                "content": MARKER + " fixture", "dependencies": [SOURCE], "archived": False}

    def test_module_json_tool_result_is_parsed_without_credentials(self):
        transport = CortexToolTransport(lambda tool, args: {"content": [{"type": "text", "text": json.dumps(self.result())}]})
        self.assertEqual(transport.get(TARGET).dependencies, (SOURCE,))

    def test_only_exact_observed_missing_response_is_absence(self):
        missing = {"isError": True, "structuredContent": {"error_code": "INVALID_ARGUMENT"},
                   "content": [{"type": "text", "text": "module matching query does not exist"}]}
        self.assertIsNone(CortexToolTransport(lambda *args: missing).get(TARGET))
        missing["content"][0]["text"] = "invalid request"
        with self.assertRaises(ToolFailure):
            CortexToolTransport(lambda *args: missing).get(TARGET)

    def test_generic_error_or_malformed_result_never_means_absent(self):
        for result in ({"isError": True}, {}, {"structuredContent": dict(self.result(), version=True)}):
            with self.subTest(result=result), self.assertRaises(ToolFailure):
                CortexToolTransport(lambda *args: result).get(TARGET)

    def test_update_omits_metadata_and_requires_matching_acknowledgment(self):
        calls = []
        def invoke(tool, args):
            calls.append((tool, args))
            return {"structuredContent": self.result()}
        CortexToolTransport(invoke).update(TARGET, self.result()["content"], (SOURCE,))
        self.assertEqual(calls[0][0], "context_update")
        self.assertEqual(set(calls[0][1]), {"name", "content", "dependencies"})
        with self.assertRaises(ToolFailure):
            CortexToolTransport(lambda *args: {}).create(TARGET, MARKER, ())
