"""Synthetic subprocess ports; no authenticated provider/storage evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_versioned_custody_dispatcher as fixtures


class SingleTranscriptCliTests(unittest.TestCase):
    receive = fixtures.ConnectedCustodyCliTests.receive
    serve = fixtures.ConnectedCustodyCliTests.serve

    def setUp(self):
        fixtures.ConnectedCustodyCliTests.setUp(self)
        self.config = dict(supervised=self.config['supervised'],
                           custody_key='synthetic-single-transcript',
                           custody_head_reference='synthetic-head')
        self.key = self.config['custody_key']
        self.service = fixtures.Service(self.key)

    def start(self, flags=(), journal=None):
        self.path.write_text(json.dumps(self.config))
        process = subprocess.Popen([sys.executable, '-m',
            'nexus_sandbox.custodied_supervised_cli', '--config', str(self.path),
            '--journal', str(journal or self.journal), *flags],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / 'src')))
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
        self.addCleanup(cleanup)
        return process

    def test_create_readonly_replay_restore_and_receipt_boundary(self):
        first = self.serve(self.start(('--initialize', '--allow-create')))
        self.assertEqual(first['result']['execution']['handoff']['status'], 'READBACK_MATCHED')
        self.assertFalse(first['transaction_complete'])
        self.assertEqual(first['next_action'], 'RETAIN_AND_INDEPENDENTLY_READ_EXECUTION_RECEIPT')
        for flags, path in [((), self.journal), (('--restore',), self.root / 'restore.sqlite')]:
            result = self.serve(self.start(flags, path))
            self.assertEqual(result['result']['custody_status'], 'JOURNAL_READBACK_MATCHED')
            self.assertEqual(result['result']['execution']['create_requests'], 0)
            self.assertFalse(result['transaction_complete'])
        self.assertEqual(self.creates, 1)

    def test_default_mode_does_not_create(self):
        result = self.serve(self.start(('--initialize',)))
        self.assertEqual(result['result']['execution']['handoff']['status'], 'BLOCKED')
        self.assertEqual(self.creates, 0)

    def test_lost_storage_reply_never_reaches_provider_create(self):
        result = self.serve(self.start(('--initialize', '--allow-create')), drop_replace_reply=True)
        self.assertEqual(result['type'], 'blocked')
        self.assertEqual(self.creates, 0)

    def test_version_conflict_stops(self):
        self.service.race = True
        self.assertEqual(self.serve(self.start(('--initialize', '--allow-create')))['type'], 'blocked')
        self.assertEqual(self.creates, 0)

    def test_wrong_response_id_stops(self):
        self.assertEqual(self.serve(self.start(('--initialize', '--allow-create')), wrong_id=True)['type'], 'blocked')
        self.assertEqual(self.creates, 0)

    def test_missing_or_misbound_gate_fails_before_journal_or_storage(self):
        for change in ('missing', 'misbound'):
            with self.subTest(change=change):
                gate = self.config['supervised']['analysis_gate']
                if change == 'missing':
                    del self.config['supervised']['analysis_gate']
                else:
                    self.config['supervised']['output_name'] = 'different-destination'
                self.assertEqual(self.receive(self.start(('--initialize', '--allow-create')))['type'], 'blocked')
                self.assertFalse(self.journal.exists())
                self.assertEqual(self.service.calls, [])
                self.config['supervised']['analysis_gate'] = gate

    def test_restore_cannot_enable_writes(self):
        self.assertEqual(self.receive(self.start(('--restore', '--allow-create')))['type'], 'blocked')
        self.assertFalse(self.journal.exists())
        self.assertEqual(self.service.calls, [])
