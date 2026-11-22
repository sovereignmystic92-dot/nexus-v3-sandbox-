"""Synthetic storage/provider ports; no authentication or live acceptance."""
import copy
import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from nexus_sandbox.supervised_journal_custody import (
    JournalCustody, execute_custodied_supervised, expected_binding,
)
from nexus_sandbox.transcript_ingestion_gate import prepare_transcript
from supervised_test_support import make_gate


class Store:
    def __init__(self):
        self.pointer = None
        self.objects = {}
        self.fault = None

    def retain(self, content):
        if self.fault == 'retain' and json.loads(content)['generation'] == 2:
            raise OSError('synthetic storage failure')
        ref = 'synthetic:' + str(len(self.objects) + 1)
        self.objects[ref] = content
        return ref

    def read(self, ref):
        value = self.objects[ref]
        if self.fault == 'corrupt' and json.loads(value)['generation'] == 2:
            return b'corrupt'
        return value

    def head(self, key):
        return copy.deepcopy(self.pointer)

    def cas(self, key, previous, new):
        if self.fault == 'cas' and new['generation'] == 2:
            return False
        if self.pointer != previous:
            return False
        self.pointer = copy.deepcopy(new)
        return True

    def custody(self, binding):
        return JournalCustody('synthetic-work', binding, retain=self.retain,
            read=self.read, head=self.head, cas=self.cas)


class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'journal.sqlite'
        prepared = prepare_transcript('Synthetic source. ' * 30, 256)
        self.args = dict(journal_path=self.path, prepared=prepared,
            source_page='11111111-1111-4111-8111-111111111111',
            source_sha256=prepared['receipt']['sha256'], output_name='synthetic-output',
            analysis='Synthetic source-attributed result', expected_owner='synthetic-owner',
            allow_create=True)
        self.args['analysis_gate'] = make_gate(self.args['source_page'],
            self.args['source_sha256'], self.args['output_name'], self.args['analysis'])
        self.store = Store()
        self.binding = expected_binding(self.args)
        self.module = None
        self.creates = 0
        self.crash = False
        self.commit = True

    def request(self, op, payload):
        if op == 'archive_read':
            return dict(destination=self.args['source_page'],
                source_sha256=self.args['source_sha256'], complete=True,
                chunks=[dict(index=i, text=t) for i, t in enumerate(self.args['prepared']['chunks'])])
        if op == 'cortex_get':
            return copy.deepcopy(self.module)
        if op == 'cortex_create':
            self.creates += 1
            custody = self.store.custody(self.binding)
            journal = custody.load(custody.current())
            with tempfile.NamedTemporaryFile() as saved:
                saved.write(journal)
                saved.flush()
                with sqlite3.connect(saved.name) as db:
                    assert db.execute('SELECT state FROM execution').fetchone()[0] == 'INTENT'
            if self.commit:
                self.module = dict(id='synthetic-module', name=payload['name'],
                    owner='synthetic-owner', version=1, content=payload['content'])
            if self.crash:
                raise SystemExit('synthetic abrupt interruption')
            return {}
        raise AssertionError(op)

    def run_host(self, initialize=False, **overrides):
        args = dict(self.args, request=self.request)
        args.update(overrides)
        return execute_custodied_supervised(custody=self.store.custody(self.binding),
                                            initialize=initialize, **args)

    def test_intent_is_readback_verified_before_one_create_and_replay(self):
        result = self.run_host(initialize=True)
        self.assertEqual(result['execution']['handoff']['status'], 'READBACK_MATCHED')
        self.assertFalse(result['remote_fencing'])
        self.assertEqual(self.run_host(allow_create=False)['execution']['create_requests'], 0)
        self.assertEqual(self.creates, 1)

    def test_storage_failure_at_intent_makes_no_provider_create(self):
        for fault in ('retain', 'corrupt', 'cas'):
            with self.subTest(fault=fault):
                self.path = Path(self.tmp.name) / (fault + '.sqlite')
                self.args['journal_path'] = self.path
                self.store = Store()
                self.store.fault = fault
                with self.assertRaises((ValueError, OSError)):
                    self.run_host(initialize=True)
                self.assertEqual(self.creates, 0)

    def test_missing_gate_blocks_before_journal_or_storage(self):
        with self.assertRaises((ValueError, TypeError)):
            self.run_host(initialize=True, analysis_gate=None)
        self.assertFalse(self.path.exists())
        self.assertEqual(self.store.objects, {})

    def test_unknown_transaction_cannot_be_implicitly_initialized(self):
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertFalse(self.path.exists())

    def test_initialize_cannot_replace_retained_or_local_transaction(self):
        self.run_host(initialize=True)
        with self.assertRaises(ValueError):
            self.run_host(initialize=True)
        self.assertEqual(self.creates, 1)

    def test_restore_uncertain_commit_reconciles_without_second_create(self):
        self.crash = True
        with self.assertRaises(SystemExit):
            self.run_host(initialize=True)
        restored = Path(self.tmp.name) / 'restored.sqlite'
        self.store.custody(self.binding).restore(restored)
        self.crash = False
        result = self.run_host(journal_path=restored, allow_create=False)
        self.assertEqual(result['execution']['handoff']['status'], 'READBACK_MATCHED')
        self.assertEqual(self.creates, 1)

    def test_restore_uncertain_absence_never_releases_intent(self):
        self.crash, self.commit = True, False
        with self.assertRaises(SystemExit):
            self.run_host(initialize=True)
        restored = Path(self.tmp.name) / 'absent.sqlite'
        self.store.custody(self.binding).restore(restored)
        self.crash = False
        self.assertEqual(self.run_host(journal_path=restored)['execution']['handoff']['status'], 'BLOCKED')
        self.assertEqual(self.creates, 1)

    def test_restore_never_overwrites_existing_journal(self):
        self.run_host(initialize=True)
        before = self.path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.store.custody(self.binding).restore(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_missing_pointer_blocks_even_with_local_journal(self):
        self.run_host(initialize=True)
        self.store.pointer = None
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertEqual(self.creates, 1)

    def test_wrong_binding_or_corrupt_object_cannot_restore(self):
        self.run_host(initialize=True)
        target = Path(self.tmp.name) / 'bad.sqlite'
        with self.assertRaises(ValueError):
            self.store.custody('different binding').restore(target)
        self.store.objects[self.store.pointer['reference']] = b'changed'
        with self.assertRaises(ValueError):
            self.store.custody(self.binding).restore(target)
        self.assertFalse(target.exists())

    def test_wal_snapshot_retains_committed_intent(self):
        from nexus_sandbox.supervised_journal_custody import _snapshot, _inspect
        with sqlite3.connect(self.path) as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE execution(singleton,binding,state,module_id)')
            db.execute('INSERT INTO execution VALUES(1,?,?,NULL)', (self.binding, 'INTENT'))
            db.commit()
            self.assertEqual(_inspect(_snapshot(self.path), self.binding), ('INTENT', None))

    def test_cas_competing_pointer_prevents_effect(self):
        original = self.store.cas
        def raced(key, prior, new):
            if new['generation'] == 2:
                self.store.pointer = dict(new, reference='synthetic:competitor')
                return False
            return original(key, prior, new)
        self.store.cas = raced
        with self.assertRaises(ValueError):
            self.run_host(initialize=True)
        self.assertEqual(self.creates, 0)

    def test_pointer_disappearance_after_cas_prevents_effect(self):
        original = self.store.cas
        def vanished(key, prior, new):
            result = original(key, prior, new)
            if new['generation'] == 2:
                self.store.pointer = None
            return result
        self.store.cas = vanished
        with self.assertRaises(ValueError):
            self.run_host(initialize=True)
        self.assertEqual(self.creates, 0)

    def test_abrupt_process_exit_restores_retained_intent_and_reuses_effect(self):
        state_path = Path(self.tmp.name) / 'external-store.json'
        script = '''
import base64,json,os,sys
from pathlib import Path
from test_supervised_journal_custody import CustodyTests
t=CustodyTests();t.setUp()
t.path=Path(sys.argv[1]);t.args['journal_path']=t.path
original=t.request
def request(op,payload):
    value=original(op,payload)
    if op=='cortex_create':
        Path(sys.argv[2]).write_text(json.dumps(dict(pointer=t.store.pointer,
            objects={k:base64.b64encode(v).decode() for k,v in t.store.objects.items()},
            module=t.module)))
        os._exit(23)
    return value
t.request=request
t.run_host(initialize=True)
'''
        import os
        environment = dict(os.environ, PYTHONPATH='src:tests/unit')
        result = subprocess.run([sys.executable, '-c', script, str(self.path), str(state_path)],
                                env=environment, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 23, result.stderr.decode())
        state = json.loads(state_path.read_text())
        self.store.pointer = state['pointer']
        self.store.objects = {k: base64.b64decode(v) for k, v in state['objects'].items()}
        self.module = state['module']
        restored = Path(self.tmp.name) / 'process-restored.sqlite'
        self.store.custody(self.binding).restore(restored)
        result = self.run_host(journal_path=restored, allow_create=False)
        self.assertEqual(result['execution']['handoff']['status'], 'READBACK_MATCHED')
        self.assertEqual(self.creates, 0)

    def test_connected_wrapper_preserves_pending_receipt_gate(self):
        from nexus_sandbox.source_connection_plan import prepare_connection_plan
        from nexus_sandbox.supervised_journal_custody import execute_custodied_connected
        envelope = dict(document_id='notion:' + self.args['source_page'],
            source_url='https://app.notion.com/p/' + self.args['source_page'].replace('-', ''),
            source_revision='synthetic-revision', transcript=''.join(self.args['prepared']['chunks']),
            expected_sha256=self.args['source_sha256'])
        plan = prepare_connection_plan(envelope, mission_id='synthetic-test',
                                       code_revision='a' * 40, policy_revision='synthetic-policy')
        result = execute_custodied_connected(custody=self.store.custody(self.binding),
            initialize=True, plan=plan, consumer='csf',
            supervised_kwargs=dict(self.args, request=self.request),
            read_source_reference=lambda document_id: copy.deepcopy(plan['source']),
            read_retained_receipt=lambda work_key: None)
        self.assertEqual(result['execution']['status'], 'PENDING_RECEIPT')
        self.assertEqual(self.creates, 1)

    def test_connected_retained_receipt_reentry_verifies_and_retains_final_journal(self):
        from nexus_sandbox.source_connection_plan import prepare_connection_plan
        from nexus_sandbox.supervised_journal_custody import execute_custodied_connected, _inspect
        envelope = dict(document_id='notion:' + self.args['source_page'],
            source_url='https://app.notion.com/p/' + self.args['source_page'].replace('-', ''),
            source_revision='synthetic-revision', transcript=''.join(self.args['prepared']['chunks']),
            expected_sha256=self.args['source_sha256'])
        plan = prepare_connection_plan(envelope, mission_id='synthetic-test',
                                       code_revision='a' * 40, policy_revision='synthetic-policy')
        retained = None
        reads = []
        def receipt_reader(work_key):
            reads.append(work_key)
            return copy.deepcopy(retained)
        def run(initialize):
            return execute_custodied_connected(custody=self.store.custody(self.binding),
                initialize=initialize, plan=plan, consumer='csf',
                supervised_kwargs=dict(self.args, request=self.request, allow_create=initialize),
                read_source_reference=lambda document_id: copy.deepcopy(plan['source']),
                read_retained_receipt=receipt_reader)
        pending = run(True)
        self.assertEqual(pending['execution']['status'], 'PENDING_RECEIPT')
        self.assertEqual(pending['custody_head']['generation'], 3)
        retained = dict(reference='synthetic:retained-execution-receipt',
            content=json.dumps(pending['execution']['receipt_to_retain']).encode())
        before = len(reads)
        result = run(False)
        connected = result['execution']
        self.assertEqual(connected['status'], 'CONSUMER_PERSISTENCE_READBACK_MATCHED')
        self.assertEqual(connected['receipt_sha256'], hashlib.sha256(retained['content']).hexdigest())
        self.assertGreaterEqual(len(reads) - before, 2)
        self.assertEqual(result['custody_head']['generation'], 5)
        custody = self.store.custody(self.binding)
        self.assertEqual(_inspect(custody.load(custody.current()), self.binding),
                         ('VERIFIED', 'synthetic-module'))
        self.assertEqual(self.creates, 1)

    def test_cas_mutating_its_arguments_cannot_change_local_heads(self):
        original = self.store.cas
        def mutating(key, previous, new):
            result = original(key, previous, new)
            if previous is not None:
                previous.clear()
            new['generation'] = 999
            return result
        self.store.cas = mutating
        result = self.run_host(initialize=True)
        self.assertEqual(result['custody_head'], self.store.pointer)
        self.assertEqual(result['custody_head']['generation'], 3)
        self.assertEqual(self.creates, 1)

    def test_restore_creates_private_file_under_permissive_umask(self):
        import os
        import stat
        self.run_host(initialize=True)
        restored = Path(self.tmp.name) / 'private.sqlite'
        previous_umask = os.umask(0)
        try:
            with mock.patch('nexus_sandbox.supervised_journal_custody.os.chmod',
                            side_effect=AssertionError('Must not rely on later chmod')):
                self.store.custody(self.binding).restore(restored)
            self.assertEqual(stat.S_IMODE(restored.stat().st_mode), 0o600)
        finally:
            os.umask(previous_umask)

    def test_nonfinite_envelope_is_rejected_during_json_parsing(self):
        self.run_host(initialize=True)
        head = self.store.pointer
        original = json.loads(self.store.objects[head['reference']])
        for constant in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(constant=constant):
                obj = dict(original, journal_b64=constant)
                content = json.dumps(obj).encode()
                self.store.objects[head['reference']] = content
                self.store.pointer = dict(head, sha256=hashlib.sha256(content).hexdigest())
                with self.assertRaisesRegex(ValueError, 'Nonfinite custody JSON'):
                    self.store.custody(self.binding).load(self.store.pointer)

    def test_retained_verified_identity_cannot_be_downgraded(self):
        self.run_host(initialize=True)
        head = self.store.pointer
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE execution SET state='INTENT',module_id=NULL")
        with self.assertRaises(ValueError):
            self.store.custody(self.binding).checkpoint(self.path, head)
        self.assertEqual(self.store.pointer, head)

    def test_final_custody_failure_retains_intent_after_actual_synthetic_effect(self):
        original = self.store.retain
        def retain(content):
            if json.loads(content)['generation'] == 3:
                raise OSError('synthetic final storage failure')
            return original(content)
        self.store.retain = retain
        with self.assertRaises(OSError):
            self.run_host(initialize=True)
        self.assertEqual(self.creates, 1)
        restored = Path(self.tmp.name) / 'final-failure.sqlite'
        self.store.custody(self.binding).restore(restored)
        self.store.retain = original
        self.assertEqual(self.run_host(journal_path=restored, allow_create=False)
                         ['execution']['handoff']['status'], 'READBACK_MATCHED')
        self.assertEqual(self.creates, 1)


if __name__ == '__main__':
    unittest.main()
