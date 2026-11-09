import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.transcript_ingestion_gate import prepare_transcript
from nexus_sandbox.transcript_supervised_host import execute_supervised


class QualitySupervisedHostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'quality.sqlite'
        self.prepared = prepare_transcript('Synthetic source [music].\n' * 20, 256)
        self.page = '4128c067-daa4-8132-ad77-c54099580940'
        self.sha = self.prepared['receipt']['sha256']
        self.analysis = 'Synthetic source-linked analysis with limitations.'
        self.desired = ('NEXUS_SOURCE_PAGE=' + self.page +
                        '\nNEXUS_SOURCE_SHA256=' + self.sha + '\n' + self.analysis)
        binding = dict(run_id='quality-run', source_id=self.page,
                       source_sha256=self.sha, output_id='fixture',
                       output_sha256=hashlib.sha256(self.desired.encode()).hexdigest())
        domain = dict(name='Technology', relevance='Source is relevant.',
                      contribution='A bounded finding.',
                      knowledge_impact='Existing claims remain qualified.',
                      full_potential='Compare with another source.',
                      required_action=dict(status='NOT_REQUIRED',
                                           reason='No required action identified.',
                                           evidence_refs=[]),
                      questions='What evidence could distinguish alternatives?',
                      verification=dict(status='VERIFIED',
                                        evidence_refs=['assessment:source-bound']))
        self.gate = dict(binding=binding, required_domains=('Technology',),
                         report=dict(schema='nexus.analysis-evidence.v1',
                                     binding=copy.deepcopy(binding),
                                     output_text=self.desired, domains=[domain]))
        self.module = None
        self.calls = []
        self.fault = None

    def request(self, op, data):
        self.calls.append(op)
        if op == 'archive_read':
            return dict(destination=self.page, source_sha256=self.sha, complete=True,
                        chunks=[dict(index=i, text=text)
                                for i, text in enumerate(self.prepared['chunks'])])
        if op == 'cortex_get':
            value = copy.deepcopy(self.module)
            if self.fault == 'changed-readback' and value:
                value['content'] += ' Wrong saved content.'
            return value
        if op == 'cortex_create':
            if self.fault != 'absent':
                self.module = dict(id='module_fixture', name=data['name'],
                                   owner='owner', version=1, content=data['content'])
            if self.fault in ('committed', 'absent'):
                raise TimeoutError('PRIVATE_PROVIDER_DETAIL')
            return {}
        raise AssertionError(op)

    def run_host(self, **overrides):
        args = dict(journal_path=self.path, prepared=self.prepared,
                    source_page=self.page, source_sha256=self.sha,
                    output_name='fixture', analysis=self.analysis,
                    expected_owner='owner', request=self.request,
                    allow_create=True, analysis_gate=self.gate)
        args.update(overrides)
        return execute_supervised(**args)

    def test_gated_create_then_readonly_replay(self):
        first = self.run_host()
        self.assertEqual(first['analysis_evidence_status'], 'STRUCTURAL_READBACK_MATCHED')
        before = len(self.calls)
        second = self.run_host(allow_create=False)
        self.assertEqual(second['analysis_evidence_sha256'], first['analysis_evidence_sha256'])
        self.assertEqual(second['create_requests'], 0)
        self.assertEqual(self.calls[before:], ['archive_read', 'cortex_get', 'archive_read'])
        self.assertEqual(self.calls.count('cortex_create'), 1)

    def test_missing_domain_blocks_before_any_provider_request(self):
        self.gate['report']['domains'] = []
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertEqual(self.calls, [])
        self.assertFalse(self.path.exists())

    def test_gate_must_bind_actual_source_destination_and_prefixed_text(self):
        original = copy.deepcopy(self.gate)
        for field, bad in [('source_id', 'other-source'), ('source_sha256', 'b'*64),
                           ('output_id', 'other-destination')]:
            with self.subTest(field=field):
                self.gate = copy.deepcopy(original)
                self.gate['binding'][field] = bad
                self.gate['report']['binding'][field] = bad
                with self.assertRaises(ValueError):
                    self.run_host()
                self.assertEqual(self.calls, [])
        self.gate = copy.deepcopy(original)
        self.gate['report']['output_text'] = self.analysis
        digest = hashlib.sha256(self.analysis.encode()).hexdigest()
        self.gate['binding']['output_sha256'] = digest
        self.gate['report']['binding']['output_sha256'] = digest
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertEqual(self.calls, [])

    def test_removing_gate_cannot_downgrade_existing_journal(self):
        self.run_host()
        self.calls.clear()
        with self.assertRaises(ValueError):
            self.run_host(analysis_gate=None)
        self.assertEqual(self.calls, [])

    def test_changed_assessment_cannot_rebind_verified_journal(self):
        self.run_host()
        self.calls.clear()
        self.gate['report']['domains'][0]['verification']['evidence_refs'] = ['changed:assessment']
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertEqual(self.calls, [])

    def test_existing_ungated_journal_cannot_be_silently_upgraded(self):
        self.run_host(analysis_gate=None)
        self.calls.clear()
        with self.assertRaises(ValueError):
            self.run_host(allow_create=False)
        self.assertEqual(self.calls, [])

    def test_actual_changed_provider_content_never_verifies(self):
        self.fault = 'changed-readback'
        with self.assertRaises(ValueError):
            self.run_host()
        self.assertEqual(self.calls.count('cortex_create'), 1)
        self.fault = None
        result = self.run_host(allow_create=False)
        self.assertEqual(result['analysis_evidence_status'], 'STRUCTURAL_READBACK_MATCHED')
        self.assertEqual(result['create_requests'], 0)

    def test_uncertain_create_precheck_is_not_saved_quality_success(self):
        self.fault = 'committed'
        result = self.run_host()
        self.assertEqual(result['handoff']['status'], 'BLOCKED')
        self.assertEqual(result['analysis_evidence_status'], 'PRECHECK_ONLY')
        self.assertNotIn('PRIVATE_PROVIDER_DETAIL', repr(result))
        self.fault = None
        result = self.run_host(allow_create=False)
        self.assertEqual(result['analysis_evidence_status'], 'STRUCTURAL_READBACK_MATCHED')
        self.assertEqual(self.calls.count('cortex_create'), 1)

    def test_uncertain_absence_does_not_release_create_intent(self):
        self.fault = 'absent'
        self.run_host()
        self.fault = None
        result = self.run_host()
        self.assertEqual(result['handoff']['status'], 'BLOCKED')
        self.assertEqual(result['analysis_evidence_status'], 'PRECHECK_ONLY')
        self.assertEqual(self.calls.count('cortex_create'), 1)

    def test_readonly_absence_does_not_claim_quality_readback(self):
        result = self.run_host(allow_create=False)
        self.assertEqual(result['analysis_evidence_status'], 'PRECHECK_ONLY')
        self.assertEqual(result['create_requests'], 0)


if __name__ == '__main__':
    unittest.main()
