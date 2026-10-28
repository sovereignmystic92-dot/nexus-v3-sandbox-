from dataclasses import replace
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nexus_sandbox.operation_journal import Operation, OperationJournal
from nexus_sandbox.record_readback import Observation, digest

ROOT = '00000000-0000-0000-0000-000000000001'
PAGE = '00000000-0000-0000-0000-000000000002'
OTHER = '00000000-0000-0000-0000-000000000003'


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'private.sqlite'
        self.j = OperationJournal.initialize(self.path, 'pilot-journal')
        self.op = Operation('request-one', 'source-one', 'revision-one', ROOT,
                            digest('private payload'))
        self.page = Observation(PAGE, ROOT, 'private payload', True)

    def test_restart_after_intent_blocks_second_write_attempt(self):
        self.assertEqual(self.j.begin(self.op), 'MAY_ATTEMPT_WRITE')
        restart = OperationJournal(self.path, 'pilot-journal')
        self.assertEqual(restart.begin(self.op), 'RECONCILE_ONLY')

    def test_uncertain_create_reconciles_without_create_callback(self):
        self.j.begin(self.op)
        restart = OperationJournal(self.path, 'pilot-journal')
        result = restart.reconcile(self.op, PAGE, lambda _: self.page)
        self.assertEqual(result.status, 'VERIFIED_OBSERVATION')
        self.assertEqual(restart.begin(self.op), 'RECONCILE_ONLY')

    def test_all_changed_bindings_rejected(self):
        self.j.begin(self.op)
        for change in ({'source_id': 'different'}, {'source_revision': 'different'},
                       {'destination_id': OTHER}, {'payload_sha256': digest('different')}):
            with self.assertRaises(ValueError):
                self.j.begin(replace(self.op, **change))

    def test_acknowledgment_does_not_skip_readback(self):
        self.j.begin(self.op)
        self.j.acknowledge(self.op, PAGE)
        calls = []
        def reader(identifier):
            calls.append(identifier)
            return self.page
        self.assertEqual(self.j.reconcile(self.op, PAGE, reader).status,
                         'VERIFIED_OBSERVATION')
        self.assertEqual(len(calls), 1)

    def test_changed_identity_is_blocked_before_read(self):
        self.j.begin(self.op)
        self.j.acknowledge(self.op, PAGE)
        with self.assertRaises(ValueError):
            self.j.reconcile(self.op, OTHER, lambda _: self.fail('must not read'))

    def test_mismatch_and_outage_never_enable_retry(self):
        self.j.begin(self.op)
        self.assertEqual(self.j.reconcile(self.op, PAGE, lambda _: replace(
            self.page, payload='different')).status, 'MISMATCH')
        def failure(_):
            raise TimeoutError()
        self.assertEqual(self.j.reconcile(self.op, PAGE, failure).status, 'UNKNOWN')
        self.assertEqual(self.j.begin(self.op), 'RECONCILE_ONLY')

    def test_missing_journal_not_silently_recreated(self):
        self.path.unlink()
        with self.assertRaises(sqlite3.OperationalError):
            OperationJournal(self.path, 'pilot-journal')
        self.assertFalse(self.path.exists())

    def test_existing_file_and_wrong_identity_hold(self):
        with self.assertRaises(FileExistsError):
            OperationJournal.initialize(self.path, 'replacement')
        with self.assertRaises(ValueError):
            OperationJournal(self.path, 'wrong-identity')

    def test_payload_not_stored_in_journal(self):
        self.j.begin(self.op)
        self.assertNotIn(b'private payload', self.path.read_bytes())

    def test_two_handles_share_single_intent(self):
        other = OperationJournal(self.path, 'pilot-journal')
        self.assertEqual(self.j.begin(self.op), 'MAY_ATTEMPT_WRITE')
        self.assertEqual(other.begin(self.op), 'RECONCILE_ONLY')
