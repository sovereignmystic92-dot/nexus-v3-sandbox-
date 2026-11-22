import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.connected_supervised_host import execute_connected_supervised
from nexus_sandbox.source_connection_plan import prepare_connection_plan
from nexus_sandbox.transcript_ingestion_gate import prepare_transcript
from supervised_test_support import make_gate


class ConnectedHostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.page = "00000000-0000-0000-0000-000000000001"
        raw = "Synthetic transcript Ω.\n" * 20
        self.prepared = prepare_transcript(raw, 256)
        self.sha = self.prepared["receipt"]["sha256"]
        self.plan = prepare_connection_plan(dict(
            source_url="https://app.notion.com/p/" + self.page.replace("-", ""),
            document_id="notion:" + self.page, source_revision="synthetic-revision-1",
            transcript=raw, expected_sha256=self.sha), mission_id="synthetic-test",
            code_revision="a" * 40, policy_revision="synthetic-policy-1")
        self.module = None
        self.calls = []
        self.saved = {}
        self.receipt_calls = []
        self.fault = None
        self.source_observation = copy.deepcopy(self.plan["source"])
        self.args = dict(journal_path=Path(self.tmp.name)/"execution.sqlite",
            prepared=self.prepared, source_page=self.page, source_sha256=self.sha,
            output_name="fixture", analysis="Synthetic derived result", expected_owner="owner",
            request=self.request, allow_create=True,
            analysis_gate=make_gate(self.page, self.sha, "fixture", "Synthetic derived result"))

    def request(self, operation, payload):
        self.calls.append(operation)
        if operation == "archive_read":
            return dict(destination=self.page, source_sha256=self.sha, complete=True,
                        chunks=[dict(index=i, text=chunk)
                                for i, chunk in enumerate(self.prepared["chunks"])])
        if operation == "cortex_get":
            return copy.deepcopy(self.module)
        if operation == "cortex_create":
            if self.fault != "uncertain_absent":
                self.module = dict(id="synthetic-module", name=payload["name"],
                                   owner="owner", version=1, content=payload["content"])
            if self.fault == "uncertain_absent":
                raise TimeoutError()
            return None
        raise AssertionError(operation)

    def read_receipt(self, key):
        self.receipt_calls.append(key)
        if self.fault == "receipt_read":
            raise TimeoutError()
        return copy.deepcopy(self.saved.get(key))

    def run_connected(self, **changes):
        params = dict(plan=self.plan, consumer="knowledge_development",
            supervised_kwargs=self.args,
            read_source_reference=lambda key: copy.deepcopy(self.source_observation),
            read_retained_receipt=self.read_receipt)
        params.update(changes)
        return execute_connected_supervised(**params)

    def save_pending(self):
        result = self.run_connected()
        key = result["work_key"]
        self.saved[key] = dict(reference="synthetic:retained-receipt",
                               content=json.dumps(result["receipt_to_retain"]).encode())
        return key

    def test_missing_receipt_is_pending_after_verified_output(self):
        result = self.run_connected()
        self.assertEqual(result["status"], "PENDING_RECEIPT")
        self.assertEqual(result["execution"]["handoff"]["status"], "READBACK_MATCHED")
        self.assertNotIn("receipt_ref", result)
        self.assertEqual(self.calls.count("cortex_create"), 1)

    def test_retained_create_receipt_reconciles_readonly_without_duplicate_write(self):
        key = self.save_pending()
        self.args["allow_create"] = False
        before = len(self.calls)
        result = self.run_connected()
        self.assertEqual(result["status"], "CONSUMER_PERSISTENCE_READBACK_MATCHED")
        self.assertEqual(result["receipt_sha256"], hashlib.sha256(self.saved[key]["content"]).hexdigest())
        self.assertEqual(self.calls[before:], ["archive_read", "cortex_get", "archive_read"] * 2)
        self.assertEqual(self.calls.count("cortex_create"), 1)
        self.assertFalse(result["other_consumers_verified"])
        self.assertFalse(result["knowledge_promoted"])

    def test_one_consumer_receipt_cannot_close_other_consumer(self):
        key = self.save_pending()
        other_key = self.plan["consumers"][1]["work_key"]
        self.saved[other_key] = self.saved[key]
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.run_connected(consumer="csf")

    def test_changed_receipt_binding_or_output_is_rejected(self):
        key = self.save_pending()
        original = self.saved[key]["content"]
        for field in ("source_key", "plan_id", "consumer", "work_key"):
            saved = json.loads(original)
            saved["binding"][field] = "changed"
            self.saved[key]["content"] = json.dumps(saved).encode()
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_connected()
        saved = json.loads(original)
        saved["execution"]["module_id"] = "different-module"
        self.saved[key]["content"] = json.dumps(saved).encode()
        with self.assertRaises(ValueError):
            self.run_connected()

    def test_receipt_read_failure_is_not_absence_or_completion(self):
        self.fault = "receipt_read"
        with self.assertRaises(TimeoutError):
            self.run_connected()
        self.assertEqual(self.calls.count("cortex_create"), 0)

    def test_receipt_callback_cannot_hide_output_mutation(self):
        key = self.save_pending()
        def mutate_output(work_key):
            self.module["content"] += " changed"
            return self.saved[key]
        with self.assertRaises(ValueError):
            self.run_connected(read_retained_receipt=mutate_output)
        self.assertEqual(self.calls.count("cortex_create"), 1)

    def test_source_revision_change_during_receipt_read_blocks(self):
        key = self.save_pending()
        def mutate_revision(work_key):
            self.source_observation["source_revision"] = "changed"
            return self.saved[key]
        result = self.run_connected(read_retained_receipt=mutate_revision)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertNotIn("receipt_ref", result)

    def test_stale_source_revision_blocks_before_provider_access(self):
        self.source_observation["source_revision"] = "changed"
        with self.assertRaises(ValueError):
            self.run_connected()
        self.assertEqual(self.calls, [])

    def test_missing_gate_or_mission_mismatch_blocks_before_provider_access(self):
        for gate in (None, {"binding": {"run_id": "different"}}):
            with self.subTest(gate=gate), self.assertRaises(ValueError):
                self.run_connected(supervised_kwargs={**self.args, "analysis_gate": gate})
        self.assertEqual(self.calls, [])

    def test_incomplete_matching_gate_rejected_before_source_metadata_read(self):
        source_calls = []
        broken = {"binding": {"run_id": "synthetic-test"}}
        with self.assertRaises(ValueError):
            self.run_connected(
                supervised_kwargs={**self.args, "analysis_gate": broken},
                read_source_reference=lambda key: source_calls.append(key))
        self.assertEqual(source_calls, [])
        self.assertEqual(self.calls, [])
        self.assertFalse(Path(self.args["journal_path"]).exists())

    def test_retained_receipt_requires_integer_create_count(self):
        key = self.save_pending()
        saved = json.loads(self.saved[key]["content"])
        saved["execution"]["create_requests"] = True
        self.saved[key]["content"] = json.dumps(saved).encode()
        with self.assertRaises(ValueError):
            self.run_connected()

    def test_tampered_plan_rejected_before_provider_access(self):
        for field, value in (("source_key", "b" * 64), ("provider_called", 0),
                             ("status", "COMPLETE")):
            changed = {**self.plan, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_connected(plan=changed)
        self.assertEqual(self.calls, [])

    def test_uncertain_absent_create_preserves_original_journal_hold(self):
        self.fault = "uncertain_absent"
        self.assertEqual(self.run_connected()["status"], "BLOCKED")
        self.fault = None
        self.assertEqual(self.run_connected()["status"], "BLOCKED")
        self.assertEqual(self.calls.count("cortex_create"), 1)
        self.assertGreater(len(self.receipt_calls), 0)

    def test_retained_receipt_blocks_replacement_create_even_without_old_journal(self):
        self.save_pending()
        self.args["journal_path"] = Path(self.tmp.name)/"declared-recovery-test.sqlite"
        self.module = None
        result = self.run_connected()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(self.calls.count("cortex_create"), 1)

    def test_receipt_disappearance_is_not_pending_or_completion(self):
        key = self.save_pending()
        calls = []
        def disappearing(work_key):
            calls.append(work_key)
            return self.saved[key] if len(calls) == 1 else None
        with self.assertRaisesRegex(ValueError, "disappeared"):
            self.run_connected(read_retained_receipt=disappearing)

    def test_malformed_duplicate_nonfinite_and_oversized_receipts_rejected(self):
        key = self.save_pending()
        for content in (b"not json", b'{"schema":1,"schema":2}',
                        b'{"score":NaN}', b" " * 1048577):
            self.saved[key]["content"] = content
            with self.subTest(size=len(content)), self.assertRaises(ValueError):
                self.run_connected()


if __name__ == "__main__":
    unittest.main()
