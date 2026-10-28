import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from nexus_sandbox.approved_writes import ApprovedWriteBoundary, WriteHold, content_hash


class ApprovedWriteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'writes.sqlite')
        self.value = {'text': 'before'}
        self.target = {'text': 'after'}
        self.before = content_hash(self.value)
        self.calls = []
        self.approvals = []
        self.boundary = ApprovedWriteBoundary(self.path, self.approve, self.read, self.write)

    def approve(self, intent, request_hash):
        self.approvals.append((intent, request_hash))
        return dict(intent, verdict='REVIEW_RECEIPTS_ACCEPTED', request_sha256=request_hash)

    def read(self, destination):
        self.assertEqual(destination, 'fixture:one')
        return self.value

    def write(self, destination, payload):
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT state FROM approved_writes').fetchone()[0],
                             'DISPATCHING')
        self.calls.append((destination, payload))
        self.value = payload

    def run_write(self, boundary=None, payload=None):
        return (boundary or self.boundary).execute('request:one', 'a' * 40, 'fixture:one',
                                                   self.before, payload or self.target)

    def test_write_readback_and_repeat_without_duplicate_action(self):
        self.assertTrue(self.run_write()['write_attempted'])
        self.assertFalse(self.run_write()['write_attempted'])
        self.assertEqual(len(self.calls), 1)

    def test_missing_or_wrong_bound_approval_prevents_write(self):
        for result in (None, {}, {'verdict': 'PASS'}):
            b = ApprovedWriteBoundary(self.path, lambda *args: result, self.read, self.write)
            with self.assertRaises(WriteHold): self.run_write(b)
        self.assertEqual(self.calls, [])

    def test_changed_destination_baseline_prevents_write(self):
        self.value = {'text': 'newer work'}
        with self.assertRaises(WriteHold): self.run_write()
        self.assertEqual(self.calls, [])

    def test_reused_request_cannot_change_payload(self):
        self.run_write()
        with self.assertRaises(WriteHold): self.run_write(payload={'text': 'other'})
        self.assertEqual(len(self.calls), 1)

    def test_lost_reply_reconciles_after_restart_without_repeating_write(self):
        def lost_reply(destination, payload):
            self.write(destination, payload)
            raise TimeoutError('lost reply')
        b = ApprovedWriteBoundary(self.path, self.approve, self.read, lost_reply)
        with self.assertRaises(WriteHold): self.run_write(b)
        restarted = ApprovedWriteBoundary(self.path, self.approve, self.read, self.write)
        self.assertFalse(self.run_write(restarted)['write_attempted'])
        self.assertEqual(len(self.calls), 1)

    def test_uncertain_unapplied_write_is_never_retried(self):
        calls = []
        def fail(*args):
            calls.append(args)
            raise TimeoutError()
        b = ApprovedWriteBoundary(self.path, self.approve, self.read, fail)
        with self.assertRaises(WriteHold): self.run_write(b)
        with self.assertRaises(WriteHold): self.run_write(b)
        self.assertEqual(len(calls), 1)

    def test_readback_mismatch_is_retained_as_uncertain(self):
        b = ApprovedWriteBoundary(self.path, self.approve, self.read, lambda *args: None)
        with self.assertRaises(WriteHold): self.run_write(b)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT state FROM approved_writes').fetchone()[0], 'UNCERTAIN')

    def test_newer_remote_work_is_not_overwritten_on_repeat(self):
        self.run_write()
        self.value = {'text': 'newer'}
        with self.assertRaises(WriteHold): self.run_write()
        self.assertEqual(len(self.calls), 1)

    def test_intent_hash_binds_baseline_payload_and_destination(self):
        self.run_write()
        intent, digest = self.approvals[0]
        self.assertEqual(intent['before_sha256'], self.before)
        self.assertEqual(intent['payload_sha256'], content_hash(self.target))
        self.assertEqual(digest, content_hash(intent))
