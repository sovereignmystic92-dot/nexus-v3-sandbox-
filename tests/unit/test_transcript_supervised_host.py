import copy
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.transcript_ingestion_gate import prepare_transcript
from nexus_sandbox.transcript_supervised_host import execute_supervised
from supervised_test_support import make_gate


class SupervisedHostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.prepared = prepare_transcript('Synthetic source [music]  \n' * 20, 256)
        self.page = '4128c067-daa4-8132-ad77-c54099580940'
        self.sha = self.prepared['receipt']['sha256']
        self.module = None
        self.calls = []
        self.fault = None
        self.gate = make_gate(self.page, self.sha, 'fixture', 'Synthetic derived result')

    def request(self, op, data):
        self.calls.append(op)
        if op == 'archive_read':
            chunks = copy.deepcopy(self.prepared['chunks'])
            if self.fault == 'source':
                chunks[0] += 'changed'
            return dict(destination=self.page, source_sha256=self.sha,
                        complete=True, chunks=[dict(index=i,text=c) for i,c in enumerate(chunks)])
        if op == 'cortex_get':
            if self.fault == 'read':
                raise TimeoutError()
            return copy.deepcopy(self.module)
        if op == 'cortex_create':
            if self.fault != 'absent':
                self.module = dict(id='module_fixture', name=data['name'], owner='owner',
                                   version=1, content=data['content'])
            if self.fault in ('committed', 'absent'):
                raise TimeoutError()
            return {}
        raise AssertionError(op)

    def run_host(self, **overrides):
        args = dict(journal_path=Path(self.tmp.name)/'run.sqlite', prepared=self.prepared,
                    source_page=self.page, source_sha256=self.sha, output_name='fixture',
                    analysis='Synthetic derived result', expected_owner='owner',
                    request=self.request, allow_create=True, analysis_gate=self.gate)
        args.update(overrides)
        return execute_supervised(**args)

    def test_create_then_fresh_readonly_replay(self):
        self.assertEqual(self.run_host()['handoff']['status'], 'READBACK_MATCHED')
        before = len(self.calls)
        result = self.run_host(allow_create=False)
        self.assertEqual(result['create_requests'], 0)
        self.assertEqual(self.calls[before:], ['archive_read','cortex_get','archive_read'])
        self.assertEqual(self.calls.count('cortex_create'), 1)

    def test_uncertain_committed_create_reconciles_without_retry(self):
        self.fault = 'committed'
        self.assertEqual(self.run_host()['handoff']['status'], 'BLOCKED')
        self.fault = None
        self.assertEqual(self.run_host()['handoff']['status'], 'READBACK_MATCHED')
        self.assertEqual(self.calls.count('cortex_create'), 1)

    def test_uncertain_absent_create_remains_blocked(self):
        self.fault = 'absent'
        self.run_host()
        self.fault = None
        self.assertEqual(self.run_host()['handoff']['status'], 'BLOCKED')
        self.assertEqual(self.calls.count('cortex_create'), 1)

    def test_source_change_prevents_cortex_access(self):
        self.fault = 'source'
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertEqual(self.calls, ['archive_read'])

    def test_owner_or_identity_change_rejected(self):
        self.run_host()
        self.module['owner'] = 'other'
        with self.assertRaises(ValueError):
            self.run_host()
        self.module['owner'] = 'owner'
        self.module['id'] = 'replacement'
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertEqual(self.calls.count('cortex_create'), 1)

    def test_binding_change_rejected_before_provider_access(self):
        self.run_host()
        count = len(self.calls)
        with self.assertRaises(ValueError):
            self.run_host(analysis='changed')
        self.assertEqual(len(self.calls), count)

    def test_failed_read_prevents_create(self):
        self.fault = 'read'
        with self.assertRaises(TimeoutError):
            self.run_host()
        self.assertNotIn('cortex_create', self.calls)

    def test_denied_create_makes_no_request(self):
        self.assertEqual(self.run_host(allow_create=False)['handoff']['status'], 'BLOCKED')
        self.assertNotIn('cortex_create', self.calls)


if __name__ == '__main__':
    unittest.main()
