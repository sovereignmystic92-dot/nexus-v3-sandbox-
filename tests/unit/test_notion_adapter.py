"""Offline transport tests. These do not exercise the live Notion service."""

from dataclasses import replace
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nexus_sandbox.notion_adapter import Binding, BindingConflict, Listing, NotionAdapter, Page

ROOT = "00000000-0000-0000-0000-000000000001"
PAGE = "00000000-0000-0000-0000-000000000002"


class FakeTransport:
    def __init__(self):
        self.marker = "synthetic:notion:sandbox:v1"
        self.pages = []
        self.complete = True
        self.creates = 0
        self.fetches = 0
        self.lose_reply = False
        self.hide_lookup = False
        self.fail_fetch = False
        self.crash = False

    def sandbox_marker(self, parent):
        return self.marker

    def find_direct_children(self, parent, key):
        return Listing(tuple([] if self.hide_lookup else self.pages), self.complete)

    def create_child(self, binding):
        self.creates += 1
        self.pages.append(Page(PAGE, binding.parent_id, binding.key, binding.title,
                               binding.payload, binding.payload_sha256, True))
        if self.crash:
            raise SystemExit("simulated process interruption after server create")
        if self.lose_reply:
            raise TimeoutError("simulated response loss")
        return PAGE

    def fetch_page(self, page_id):
        self.fetches += 1
        if self.fail_fetch:
            raise TimeoutError("simulated read outage")
        return next(p for p in self.pages if p.page_id == page_id)


class NotionAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="notion-offline-")
        self.addCleanup(self.tmp.cleanup)
        self.journal = Path(self.tmp.name) / "receipts.sqlite"
        self.transport = FakeTransport()
        self.binding = Binding("synthetic:request:offline-N02", ROOT, "Synthetic transport test", "Fictional payload")
        self.adapter = self.reopen()

    def reopen(self):
        return NotionAdapter(self.journal, ROOT, self.transport)

    def test_create_requires_exact_independent_read_then_retry_reuses_id(self):
        receipt = self.adapter.ensure(self.binding)
        self.assertEqual((receipt.status, receipt.page_id), ("VERIFIED", PAGE))
        self.assertEqual(self.reopen().ensure(self.binding), receipt)
        self.assertEqual((self.transport.creates, self.transport.fetches), (1, 2))

    def test_response_loss_reconciles_after_restart_without_second_create(self):
        self.transport.lose_reply = True
        self.assertEqual(self.adapter.ensure(self.binding).status, "UNKNOWN")
        self.assertEqual(self.reopen().ensure(self.binding).status, "VERIFIED")
        self.assertEqual(self.transport.creates, 1)

    def test_interruption_after_create_leaves_durable_intent_for_recovery(self):
        self.transport.crash = True
        with self.assertRaises(SystemExit):
            self.adapter.ensure(self.binding)
        with sqlite3.connect(self.journal) as db:
            self.assertEqual(db.execute("SELECT status FROM external_receipts").fetchone()[0], "CREATE_INTENT")
        self.assertEqual(self.reopen().ensure(self.binding).status, "VERIFIED")
        self.assertEqual(self.transport.creates, 1)

    def test_absent_result_after_uncertain_create_never_recreates(self):
        self.transport.lose_reply = True
        self.adapter.ensure(self.binding)
        self.transport.hide_lookup = True
        for _ in range(3):
            self.assertEqual(self.reopen().ensure(self.binding).status, "UNKNOWN")
        self.assertEqual(self.transport.creates, 1)

    def test_acknowledged_id_survives_read_outage_and_restart(self):
        self.transport.fail_fetch = True
        self.assertEqual(self.adapter.ensure(self.binding).status, "UNKNOWN")
        self.transport.fail_fetch = False
        self.assertEqual(self.reopen().ensure(self.binding).status, "VERIFIED")
        self.assertEqual(self.transport.creates, 1)

    def test_changed_binding_rejected_before_remote_observation(self):
        self.adapter.ensure(self.binding)
        for changes in ({"payload": "changed"}, {"title": "changed"}):
            with self.subTest(changes=changes), self.assertRaises(BindingConflict):
                self.reopen().ensure(replace(self.binding, **changes))
        self.assertEqual((self.transport.creates, self.transport.fetches), (1, 1))

    def test_outside_parent_and_nonsynthetic_key_rejected_without_remote_call(self):
        for changes in ({"parent_id": PAGE}, {"key": "real-request"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.adapter.ensure(replace(self.binding, **changes))
        self.assertEqual((self.transport.creates, self.transport.fetches), (0, 0))

    def test_missing_sandbox_marker_blocks_creation(self):
        self.transport.marker = "ordinary-root"
        self.assertEqual(self.adapter.ensure(self.binding).status, "BLOCKED")
        self.assertEqual(self.transport.creates, 0)

    def test_partial_lookup_blocks_creation(self):
        self.transport.complete = False
        self.assertEqual(self.adapter.ensure(self.binding).status, "UNKNOWN")
        self.assertEqual(self.transport.creates, 0)

    def test_duplicate_matches_hold_and_preserve_both_pages(self):
        self.adapter.ensure(self.binding)
        # Fresh journal models reconciliation without a known receipt.
        second = Path(self.tmp.name) / "second.sqlite"
        self.transport.pages.append(replace(self.transport.pages[0], page_id=ROOT))
        before = list(self.transport.pages)
        self.assertEqual(NotionAdapter(second, ROOT, self.transport).ensure(self.binding).status, "AMBIGUOUS")
        self.assertEqual(self.transport.pages, before)
        self.assertEqual(self.transport.creates, 1)

    def test_tampered_payload_or_location_never_verifies_or_overwrites(self):
        self.adapter.ensure(self.binding)
        original = self.transport.pages[0]
        for changes in ({"payload": "tampered"}, {"payload_sha256": "0" * 64},
                        {"parent_id": PAGE}, {"complete": False}, {"synthetic": False},
                        {"complete": 1}, {"synthetic": 1}, {"page_id": ROOT}):
            self.transport.pages = [replace(original, **changes)]
            receipt = self.reopen().ensure(self.binding)
            self.assertNotEqual(receipt.status, "VERIFIED")
            self.assertEqual(self.transport.pages[0], replace(original, **changes))
        self.assertEqual(self.transport.creates, 1)

    def test_failure_history_is_retained_after_successful_reconciliation(self):
        self.transport.lose_reply = True
        self.adapter.ensure(self.binding)
        self.reopen().ensure(self.binding)
        with sqlite3.connect(self.journal) as db:
            self.assertEqual([r[0] for r in db.execute("SELECT status FROM external_events ORDER BY sequence")],
                             ["CREATE_INTENT", "UNKNOWN", "VERIFIED"])
