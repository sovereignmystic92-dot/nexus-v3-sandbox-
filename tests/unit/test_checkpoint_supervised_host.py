"""Synthetic native host/provider/checkpoint callbacks, not live authority."""
import copy
from pathlib import Path
import unittest

import test_transcript_supervised_host as fixture
from nexus_sandbox.checkpoint_supervised_host import execute_checkpoint_supervised


class CheckpointHostTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture.SupervisedHostTests()
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.path = Path(self.base.tmp.name) / 'ordinary.sqlite'
        self.saved = None
        self.writes = 0
        self.fault = None
        self.assignment = dict(mode='OWNER_INVOKED_SUPERVISED', transaction_id='synthetic-tx',
                               assignment_id='synthetic-assignment', actor='synthetic-owner')
        self.context = dict(transaction_id='synthetic-tx', assignment_id='synthetic-assignment',
            actor='synthetic-owner', source_revision='synthetic-source-v1', code_revision='a'*40,
            policy_revision='synthetic-policy', destination=dict(parent=None, dependencies=[]))
        self.args = dict(journal_path=self.path, prepared=self.base.prepared,
            source_page=self.base.page, source_sha256=self.base.sha, output_name='fixture',
            analysis='Synthetic derived result', expected_owner='owner', request=self.base.request,
            allow_create=True, analysis_gate=self.base.gate)

    def read(self, key):
        return copy.deepcopy(self.saved)

    def write(self, key, value):
        self.writes += 1
        if self.fault == 'before-save':
            raise TimeoutError('synthetic failure before effect')
        self.saved = copy.deepcopy(value)
        if self.fault == 'lost-reply':
            raise TimeoutError('synthetic committed intent lost reply')
        if self.fault == 'bad-readback':
            self.saved['identity']['source_sha256'] = '0'*64
        if self.fault == 'source-change':
            self.base.fault = 'source'

    def run_host(self, initialize=False, **overrides):
        args = dict(self.args, **overrides)
        return execute_checkpoint_supervised(context=self.context, supervised_kwargs=args,
            initialize=initialize, read_checkpoint=self.read, write_checkpoint=self.write,
            verify_assignment=lambda expected: copy.deepcopy(self.assignment))

    def test_create_then_readonly_replay_retains_exact_receipt(self):
        result = self.run_host(True)
        self.assertTrue(result['transaction_complete'])
        self.assertFalse(result['unattended_acceptance'])
        self.assertEqual(self.saved['state'], 'RECEIPT')
        self.assertNotIn('chunks', self.saved['identity'])
        self.assertEqual(self.writes, 2)
        self.assertTrue(self.run_host(allow_create=False)['transaction_complete'])
        self.assertEqual(self.writes, 2)
        self.assertEqual(self.base.calls.count('cortex_create'), 1)

    def test_scheduled_assignment_refused_before_journal_or_provider(self):
        self.assignment['mode'] = 'SCHEDULED'
        with self.assertRaises(PermissionError): self.run_host(True)
        self.assertFalse(self.path.exists())
        self.assertEqual(self.base.calls, [])

    def test_missing_gate_or_misbound_output_has_no_checkpoint_access(self):
        for overrides in ({'analysis_gate': None}, {'output_name': 'other'}):
            with self.assertRaises((ValueError, TypeError)): self.run_host(True, **overrides)
        self.assertEqual(self.writes, 0)
        self.assertFalse(self.path.exists())

    def test_uncertain_intent_never_retries_provider_effect(self):
        for fault in ('before-save', 'lost-reply', 'bad-readback', 'source-change'):
            with self.subTest(fault=fault):
                self.fault = fault
                # Separate explicitly synthetic test cases; never real journal resets.
                self.path = Path(self.base.tmp.name) / (fault + '.sqlite')
                self.args['journal_path'] = self.path
                self.saved = None
                self.base.fault = None
                self.run_host(True)
                self.assertNotIn('cortex_create', self.base.calls)
                self.fault = None
                self.base.fault = None
                try: self.run_host()
                except ValueError: pass
                self.assertNotIn('cortex_create', self.base.calls)

    def test_lost_journal_holds_even_with_initialize(self):
        self.run_host(True)
        self.path.unlink()
        for initialize in (False, True):
            with self.assertRaisesRegex(ValueError, 'Lost local journal'): self.run_host(initialize)
        self.assertEqual(self.base.calls.count('cortex_create'), 1)

    def test_uncertain_committed_provider_reconciles_without_second_create(self):
        self.base.fault = 'committed'
        self.assertFalse(self.run_host(True)['transaction_complete'])
        self.base.fault = None
        self.assertTrue(self.run_host(allow_create=False)['transaction_complete'])
        self.assertEqual(self.base.calls.count('cortex_create'), 1)

    def test_uncertain_absent_provider_holds_without_retry(self):
        self.base.fault = 'absent'
        self.assertFalse(self.run_host(True)['transaction_complete'])
        self.base.fault = None
        self.assertFalse(self.run_host()['transaction_complete'])
        self.assertEqual(self.base.calls.count('cortex_create'), 1)

    def test_append_cannot_use_exception(self):
        with self.assertRaises(ValueError): self.run_host(True, update_plan={})
        self.assertFalse(self.path.exists())

    def test_assignment_revoked_during_intent_retention(self):
        original = self.write
        def revoke(key, value):
            original(key, value)
            self.assignment['assignment_id'] = 'revoked'
        self.write = revoke
        self.assertFalse(self.run_host(True)['transaction_complete'])
        self.assertNotIn('cortex_create', self.base.calls)

    def test_lost_receipt_reply_reconciles_without_second_create(self):
        original = self.write
        def lose_receipt(key, value):
            original(key, value)
            if value['state'] == 'RECEIPT':
                raise TimeoutError('synthetic receipt saved, reply lost')
        self.write = lose_receipt
        with self.assertRaises(TimeoutError): self.run_host(True)
        self.write = original
        self.assertTrue(self.run_host(allow_create=False)['transaction_complete'])
        self.assertEqual(self.base.calls.count('cortex_create'), 1)

    def test_checkpoint_binding_tamper_holds_before_new_provider_access(self):
        self.run_host(True)
        self.saved['identity']['source_sha256'] = '0'*64
        calls = len(self.base.calls)
        with self.assertRaises(ValueError): self.run_host(allow_create=False)
        self.assertEqual(len(self.base.calls), calls)

    def test_destination_appearing_during_intent_save_prevents_create(self):
        original = self.write
        def competing(key, value):
            original(key, value)
            self.base.module = dict(id='other', name='fixture', owner='owner', version=1,
                                    content='unrelated')
        self.write = competing
        self.assertFalse(self.run_host(True)['transaction_complete'])
        self.assertNotIn('cortex_create', self.base.calls)
