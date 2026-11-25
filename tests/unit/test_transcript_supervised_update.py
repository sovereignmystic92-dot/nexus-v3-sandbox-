"""Synthetic providers only; no Cortex grants or live recovery attestation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from nexus_sandbox.transcript_ingestion_gate import prepare_transcript
from nexus_sandbox.transcript_supervised_host import execute_supervised
from supervised_test_support import make_gate


class SupervisedUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'update.sqlite'
        self.page = '11111111-1111-4111-8111-111111111111'
        self.prepared = prepare_transcript('Synthetic unchanged source. ' * 20, 256)
        self.sha = self.prepared['receipt']['sha256']
        self.before = dict(id='synthetic-id', name='synthetic-output', owner='synthetic-owner',
            version=7, content='Earlier analysis, unchanged.\n', dependencies=['synthetic-rule'],
            parent='synthetic-parent')
        self.module = copy.deepcopy(self.before)
        self.appendix = ('\n\nNEXUS_SOURCE_PAGE=' + self.page + '\nNEXUS_SOURCE_SHA256='
                         + self.sha + '\nNEXUS_ENRICHMENT_ID=synthetic-batch-01\n'
                         'Source-attributed new evidence only.\n')
        desired = self.before['content'] + self.appendix
        self.gate = make_gate(self.page, self.sha, self.before['name'], 'unused')
        self.gate['binding']['output_sha256'] = hashlib.sha256(desired.encode()).hexdigest()
        self.gate['report']['binding'] = copy.deepcopy(self.gate['binding'])
        self.gate['report']['output_text'] = desired
        self.calls = []
        self.fault = None
        self.source_reads = 0
        self.output_reads = 0

    def request(self, op, data):
        self.calls.append((op, copy.deepcopy(data)))
        if op == 'archive_read':
            self.source_reads += 1
            chunks = copy.deepcopy(self.prepared['chunks'])
            if self.fault == 'source' or (self.fault == 'source-after-write' and
                                          self.source_reads >= 3):
                chunks[0] += 'changed'
            return dict(destination=self.page, source_sha256=self.sha, complete=True,
                        chunks=[dict(index=i, text=c) for i, c in enumerate(chunks)])
        if op == 'cortex_get':
            self.output_reads += 1
            if self.fault == 'race' and self.output_reads == 2:
                self.module['content'] += 'outside edit'
            return copy.deepcopy(self.module)
        if op == 'cortex_update':
            # Model a trusted sole-writer dispatcher enforcing the supplied pins.
            assert data['module_id'] == self.module['id']
            assert data['expected_version'] == self.module['version']
            assert data['before_sha256'] == hashlib.sha256(self.module['content'].encode()).hexdigest()
            if self.fault == 'absent':
                raise TimeoutError('No commit observed')
            self.module['content'] = data['content']
            self.module['version'] += 1
            if self.fault == 'changed-dependency':
                self.module['dependencies'] = []
            if self.fault == 'committed':
                raise TimeoutError('Committed, acknowledgment lost')
            if self.fault == 'interrupt':
                raise KeyboardInterrupt('Process boundary simulation')
            return {'ignored_acknowledgment': True}
        raise AssertionError(op)

    def run_host(self, **overrides):
        args = dict(journal_path=self.path, prepared=self.prepared, source_page=self.page,
            source_sha256=self.sha, output_name=self.before['name'], analysis=self.appendix,
            expected_owner=self.before['owner'], request=self.request, analysis_gate=self.gate,
            update_plan=dict(before=self.before, enrichment_id='synthetic-batch-01',
                             exclusive_writer_evidence='synthetic:sole-writer'),
            allow_update=True)
        args.update(overrides)
        return execute_supervised(**args)

    def state(self):
        with sqlite3.connect(self.path) as db:
            return db.execute('SELECT state FROM execution').fetchone()[0]

    def test_one_append_preserves_base_and_replay_never_updates(self):
        result = self.run_host()
        self.assertEqual(result['handoff']['status'], 'READBACK_MATCHED')
        self.assertTrue(self.module['content'].startswith(self.before['content']))
        self.assertEqual(self.module['content'], self.before['content'] + self.appendix)
        self.assertEqual(result['module_version'], 8)
        count = len(self.calls)
        replay = self.run_host(allow_update=False)
        self.assertEqual(replay['update_requests'], 0)
        self.assertEqual([op for op, _ in self.calls[count:]],
                         ['archive_read', 'cortex_get', 'archive_read'])
        self.assertFalse(replay['remote_fencing'])
        self.assertFalse(replay['audit_promotion'])

    def test_missing_or_misbound_gate_stops_before_journal_or_provider(self):
        for gate in (None, dict(self.gate, report={})):
            with self.subTest(gate=gate):
                with self.assertRaises(ValueError):
                    self.run_host(analysis_gate=gate)
                self.assertEqual(self.calls, [])
                self.assertFalse(self.path.exists())

    def test_stale_version_content_identity_and_relationships_deny_writes(self):
        for field, value in [('version', 8), ('content', 'stale'), ('id', 'other'),
                             ('owner', 'other'), ('dependencies', []), ('parent', None)]:
            with self.subTest(field=field):
                self.module = dict(self.before, **{field: value})
                with self.assertRaises(ValueError):
                    self.run_host()
                self.assertFalse(any(op == 'cortex_update' for op, _ in self.calls))

    def test_immediate_baseline_race_is_rejected_before_intent(self):
        self.fault = 'race'
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertEqual(self.state(), 'PREPARED')
        self.assertNotIn('cortex_update', [op for op, _ in self.calls])

    def test_missing_authorization_is_readonly_and_intent_not_sent(self):
        result = self.run_host(allow_update=False)
        self.assertEqual(result['handoff']['status'], 'BLOCKED')
        self.assertEqual(result['update_requests'], 0)
        self.assertEqual(self.state(), 'PREPARED')

    def test_committed_timeout_reconciles_with_fresh_reads_and_zero_retry(self):
        self.fault = 'committed'
        self.assertEqual(self.run_host()['handoff']['status'], 'BLOCKED')
        self.assertEqual(self.state(), 'INTENT')
        self.fault = None
        self.assertEqual(self.run_host(allow_update=False)['handoff']['status'], 'READBACK_MATCHED')
        self.assertEqual(sum(op == 'cortex_update' for op, _ in self.calls), 1)

    def test_absent_uncertain_update_is_never_retried(self):
        self.fault = 'absent'
        self.run_host()
        self.fault = None
        self.assertEqual(self.run_host()['handoff']['next_action'],
                         'RECONCILE_UNCERTAIN_UPDATE_NO_RETRY')
        self.assertEqual(sum(op == 'cortex_update' for op, _ in self.calls), 1)
        self.assertEqual(self.state(), 'INTENT')

    def test_interruption_leaves_durable_intent_and_reopens_readonly(self):
        self.fault = 'interrupt'
        with self.assertRaises(KeyboardInterrupt):
            self.run_host()
        self.assertEqual(self.state(), 'INTENT')
        self.fault = None
        self.assertEqual(self.run_host(allow_update=False)['handoff']['status'], 'READBACK_MATCHED')
        self.assertEqual(sum(op == 'cortex_update' for op, _ in self.calls), 1)

    def test_source_change_before_or_after_effect_cannot_verify(self):
        self.fault = 'source'
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertNotIn('cortex_get', [op for op, _ in self.calls])
        self.fault = 'source-after-write'
        self.source_reads = 0
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertEqual(self.state(), 'INTENT')

    def test_wrong_readback_never_verifies(self):
        self.fault = 'changed-dependency'
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertEqual(self.state(), 'INTENT')

    def test_lost_journal_cannot_adopt_an_existing_matching_effect(self):
        self.run_host()
        other = Path(self.tmp.name) / 'replacement.sqlite'
        result = self.run_host(journal_path=other)
        self.assertEqual(result['handoff']['next_action'],
                         'RECONCILE_EXISTING_EFFECT_WITH_RETAINED_INTENT')
        self.assertEqual(sum(op == 'cortex_update' for op, _ in self.calls), 1)

    def test_changed_gate_or_plan_cannot_rebind_retained_intent(self):
        self.run_host(allow_update=False)
        calls = len(self.calls)
        gate = copy.deepcopy(self.gate)
        gate['report']['domains'][0]['questions'] = 'Changed evidence'
        with self.assertRaises(ValueError):
            self.run_host(analysis_gate=gate)
        self.assertEqual(len(self.calls), calls)

    def test_create_update_and_unbound_update_flags_are_rejected(self):
        for changes in (dict(allow_create=True), dict(update_plan=None), dict(allow_update=1)):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    self.run_host(**changes)
        self.assertEqual(self.calls, [])
        self.assertFalse(self.path.exists())

    def test_missing_exclusive_custody_reference_or_provenance_is_rejected(self):
        with self.assertRaises(ValueError):
            self.run_host(update_plan=dict(before=self.before, enrichment_id='synthetic-batch-01',
                                           exclusive_writer_evidence=''))
        with self.assertRaises(ValueError):
            self.run_host(analysis='\n\nUnbound appendix')
        self.assertEqual(self.calls, [])
        self.assertFalse(self.path.exists())

    def test_duplicate_enrichment_cannot_use_a_new_baseline_or_journal(self):
        self.run_host()
        prior_calls = len(self.calls)
        with self.assertRaisesRegex(ValueError, 'already present'):
            self.run_host(journal_path=Path(self.tmp.name)/'duplicate.sqlite',
                update_plan=dict(before=self.module, enrichment_id='synthetic-batch-01',
                                 exclusive_writer_evidence='synthetic:sole-writer'))
        self.assertEqual(len(self.calls), prior_calls)

    def test_conflicting_marker_and_boolean_baseline_version_fail_preflight(self):
        with self.assertRaises(ValueError):
            self.run_host(analysis=self.appendix+'NEXUS_SOURCE_PAGE=other\n')
        with self.assertRaises(ValueError):
            self.run_host(update_plan=dict(before=dict(self.before, version=True),
                enrichment_id='synthetic-batch-01', exclusive_writer_evidence='synthetic:sole-writer'))
        self.assertEqual(self.calls, [])
        self.assertFalse(self.path.exists())

    def test_existing_create_journal_cannot_be_repurposed(self):
        from supervised_test_support import seed_legacy
        seed_legacy(self.path, prepared=self.prepared, source_page=self.page,
            source_sha256=self.sha, output_name=self.before['name'],
            analysis='Original transaction', expected_owner=self.before['owner'])
        with self.assertRaisesRegex(ValueError, 'Journal binding'):
            self.run_host()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.state(), 'INTENT')

    def test_lock_rejects_another_cooperating_writer_before_provider_access(self):
        import fcntl
        with open(str(self.path)+'.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.run_host()
        self.assertEqual(self.calls, [])

    def test_fresh_process_reconciles_after_sigkill_without_second_write(self):
        root = Path(self.tmp.name)
        config = dict(journal_path=str(self.path), prepared=self.prepared, source_page=self.page,
            source_sha256=self.sha, output_name=self.before['name'], analysis=self.appendix,
            expected_owner=self.before['owner'], analysis_gate=self.gate,
            update_plan=dict(before=self.before, enrichment_id='synthetic-batch-01',
                             exclusive_writer_evidence='synthetic:sole-writer'))
        (root/'config.json').write_text(json.dumps(config))
        (root/'provider.json').write_text(json.dumps(dict(module=self.before, writes=0)))
        program = '''
import json,os,signal,sys
from pathlib import Path
from nexus_sandbox.transcript_supervised_host import execute_supervised
root=Path(sys.argv[1]); mode=sys.argv[2]
cfg=json.loads((root/'config.json').read_text())
cfg['analysis_gate']['required_domains']=tuple(cfg['analysis_gate']['required_domains'])
def request(op,data):
    if op=='archive_read':
        return dict(destination=cfg['source_page'],source_sha256=cfg['source_sha256'],
            complete=True,chunks=[dict(index=i,text=c) for i,c in enumerate(cfg['prepared']['chunks'])])
    provider=json.loads((root/'provider.json').read_text())
    if op=='cortex_get': return provider['module']
    if op!='cortex_update': raise AssertionError(op)
    provider['writes']+=1
    provider['module']['content']=data['content'];provider['module']['version']+=1
    with (root/'provider.json').open('w') as f:
        f.write(json.dumps(provider));f.flush();os.fsync(f.fileno())
    os.kill(os.getpid(),signal.SIGKILL)
result=execute_supervised(**cfg,request=request,allow_update=mode=='write')
print(json.dumps(result))
'''
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src'))
        first = subprocess.run([sys.executable, '-c', program, str(root), 'write'],
                               env=env, capture_output=True, timeout=10)
        self.assertEqual(first.returncode, -9)
        self.assertEqual(self.state(), 'INTENT')
        second = subprocess.run([sys.executable, '-c', program, str(root), 'readonly'],
                                env=env, capture_output=True, timeout=10, check=True)
        result = json.loads(second.stdout)
        self.assertEqual(result['handoff']['status'], 'READBACK_MATCHED')
        self.assertEqual(result['update_requests'], 0)
        self.assertEqual(json.loads((root/'provider.json').read_text())['writes'], 1)
        self.assertEqual(self.state(), 'VERIFIED')


if __name__ == '__main__':
    unittest.main()
