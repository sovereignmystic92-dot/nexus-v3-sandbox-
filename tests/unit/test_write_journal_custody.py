import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import test_declared_notion_write as fixture
from nexus_sandbox.approved_writes import WriteHold, content_hash
from write_journal_custody import JournalCustody, restore
import notion_tool_handoff as host


class CustodyTests(unittest.TestCase):
    observe = fixture.NotionDeclaredTests.observe
    read = fixture.NotionDeclaredTests.read
    write = fixture.NotionDeclaredTests.write
    run_adapter = fixture.NotionDeclaredTests.run_adapter
    def setUp(self):
        fixture.NotionDeclaredTests.setUp(self)
        self.store = {}

    def publish(self, envelope, digest):
        identity = str(len(self.store))
        self.store[identity] = copy.deepcopy(envelope)
        return identity

    def custody(self, fetch=None):
        return JournalCustody(self.publish, fetch or (lambda key: self.store[key]))

    def test_failed_custody_readback_prevents_remote_mutation(self):
        with self.assertRaises(WriteHold):
            self.run_adapter(custody=self.custody(lambda key: {}))
        self.assertEqual(self.calls, [])

    def test_external_dispatching_snapshot_restores_and_reconciles_in_fresh_process(self):
        custody = self.custody()
        def lost(target, value):
            self.write(target, value)
            raise TimeoutError()
        with self.assertRaises(WriteHold):
            self.run_adapter(custody=custody, write=lost)
        manifest = dict(context=self.context, rows=self.rows, target=self.target,
            before=self.before, envelope=self.store[custody.last['record_id']],
            digest=custody.last['sha256'])
        source = Path(self.temp.name) / 'saved.json'
        source.write_text(json.dumps(manifest))
        restored = str(Path(self.temp.name) / 'restored.sqlite')
        code = '''import json,sys
from write_journal_custody import restore
from declared_notion_write import execute
from declared_review_gate import OWNER_DECISION
m=json.load(open(sys.argv[1])); c=m['context']
restore(sys.argv[2],m['envelope'],expected_digest=m['digest'],request_id='synthetic:one',context=c)
def forbidden(*args): raise AssertionError('Remote mutation replayed')
r=execute(sys.argv[2],request_id='synthetic:one',context=c,author_session='author',
owner_decision=OWNER_DECISION,enrolled_destination=c['destination'],before_hash=m['before'],
payload=m['target'],observe=lambda:(c,m['rows']),read=lambda d:m['target'],write=forbidden)
assert r['state']=='VERIFIED' and r['write_attempted'] is False
print('FRESH_PROCESS_RECONCILED_NO_WRITE')
'''
        run = subprocess.run([sys.executable, '-c', code, str(source), restored],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('FRESH_PROCESS_RECONCILED_NO_WRITE', run.stdout)
        self.assertEqual(len(self.calls), 1)

    def test_changed_missing_or_misbound_custody_is_rejected(self):
        custody = self.custody()
        self.run_adapter(custody=custody)
        envelope = self.store[custody.last['record_id']]
        for digest, context, value in [('f'*64, self.context, envelope),
            (custody.last['sha256'], dict(self.context, head_sha='f'*40), envelope),
            (custody.last['sha256'], self.context, {})]:
            with self.assertRaises(WriteHold):
                restore(str(Path(self.temp.name)/'reject.sqlite'), value,
                    expected_digest=digest, request_id='synthetic:one', context=context)

    def test_restore_never_overwrites_existing_journal(self):
        custody = self.custody(); self.run_adapter(custody=custody)
        with self.assertRaises(FileExistsError):
            restore(self.journal, self.store[custody.last['record_id']],
                expected_digest=custody.last['sha256'], request_id='synthetic:one', context=self.context)

    def test_context_drift_during_custody_persistence_prevents_write(self):
        def publish(value, digest):
            identity = self.publish(value, digest)
            self.context['base_sha'] = 'f'*40
            return identity
        with self.assertRaises(WriteHold):
            self.run_adapter(custody=JournalCustody(publish, lambda key:self.store[key]))
        self.assertEqual(self.calls, [])

    def test_postwrite_custody_failure_is_not_durable_completion(self):
        reads = []
        def fetch(key):
            reads.append(key)
            return self.store[key] if len(reads)==1 else {}
        with self.assertRaises(WriteHold):
            self.run_adapter(custody=self.custody(fetch))
        self.assertEqual(len(self.calls), 1)

    def host_config(self):
        receipt = dict(schema='NXS_TOOL_HANDOFF_RECEIPT_V1', request_id='synthetic:one',
            source_id='synthetic:transcript', operation='audit_receipt',
            result='LIVE_RECEIPT_SUBMITTED')
        self.value = {'receipt': None}; self.target = {'receipt': receipt}
        self.before = content_hash(self.value)
        intent = dict(revision=self.context['head_sha'], operation='routine_write',
            destination=self.dest, before_sha256=self.before, payload_sha256=content_hash(self.target))
        self.context['request_sha256'] = content_hash(intent)
        for row in self.rows:
            row['wire'], row['digest'] = fixture.binding.bind(self.context, row['source'],
                row['agent'], row['session'], row['body'], row['evidence'])
        return dict(enrolled_destination=self.dest, context=self.context,
            request_id='synthetic:one', journal=self.journal, journal_mode='new',
            author_session='author', owner_decision=fixture.gate.OWNER_DECISION,
            before_hash=self.before, payload=self.target)

    def tool(self, method, params):
        self.assertEqual(params.get('destination', self.dest), self.dest)
        if method == 'confirm_new_enrollment': return True
        if method == 'observe_reviews': return self.observe()
        if method == 'notion_read_receipt':
            return dict(complete=True, destination=self.dest, value=self.read(self.dest))
        if method == 'notion_append_receipt':
            return self.write(self.dest, {'receipt': params['receipt']})
        if method == 'journal_publish':
            return self.publish(params['envelope'], params['expected_sha256'])
        if method == 'journal_fetch': return self.store[params['record_id']]
        self.fail('Unexpected host method')

    def test_tool_host_custody_and_receipt_end_to_end(self):
        result = host.run(self.host_config(), self.tool)
        self.assertEqual(result['state'], 'VERIFIED')
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(self.store), 2)
        self.assertEqual(result['journal_custody']['record_id'], '1')

    def test_tool_host_incomplete_receipt_observation_prevents_mutation(self):
        def tool(method, params):
            if method == 'notion_read_receipt':
                return dict(complete=False, destination=self.dest, value=self.value)
            return self.tool(method, params)
        with self.assertRaises(fixture.gate.Hold): host.run(self.host_config(), tool)
        self.assertEqual(self.calls, [])

    def test_tool_host_refuses_other_target_or_nonreceipt_payload(self):
        config = self.host_config()
        for changed in (dict(config, enrolled_destination='notion:other'),
                        dict(config, payload={'receipt': {'result': 'anything'}})):
            with self.assertRaises(fixture.gate.Hold): host.run(changed, self.tool)
        self.assertEqual(self.calls, [])

    def test_tool_host_new_mode_never_reuses_existing_journal(self):
        config = self.host_config(); host.run(config, self.tool)
        with self.assertRaises(fixture.gate.Hold): host.run(config, self.tool)
        self.assertEqual(len(self.calls), 1)


if __name__ == '__main__':
    unittest.main()
