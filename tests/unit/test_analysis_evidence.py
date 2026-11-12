import copy
import hashlib
import unittest

from nexus_sandbox.analysis_evidence import validate_analysis_evidence
from nexus_sandbox.processing_pipeline import Receipt, STAGES, run_quality_checked


class AnalysisEvidenceTests(unittest.TestCase):
    def setUp(self):
        text = 'A source-linked analysis with explicit limitations.'
        self.binding = dict(run_id='run-one', source_id='notion:source',
                            source_sha256='a' * 64, output_id='cortex:output',
                            output_sha256=hashlib.sha256(text.encode()).hexdigest())
        self.domains = ('Technology', 'Philosophy')
        def domain(name):
            return dict(name=name, relevance='Relevant to the declared question.',
                        contribution='A bounded source-derived finding.',
                        knowledge_impact='Existing understanding remains qualified.',
                        full_potential='Further comparison may test the mechanism.',
                        required_action=dict(status='NOT_REQUIRED',
                                             reason='No required mutation identified.',
                                             evidence_refs=[]),
                        questions='Is the mechanism supported in another source?',
                        verification=dict(status='VERIFIED',
                                          evidence_refs=['review:' + name]))
        self.report = dict(schema='nexus.analysis-evidence.v1',
                           binding=copy.deepcopy(self.binding), output_text=text,
                           domains=[domain(x) for x in self.domains])
        self.calls = []
        self.reads = []
        self.checkpoints = {}
        self.executors = {s: self.executor(s) for s in STAGES}

    def executor(self, stage):
        def call(prior):
            self.calls.append(stage)
            return Receipt('run-one', stage, True, ('stage:' + stage,))
        return call

    def read_evidence(self, phase):
        self.reads.append(phase)
        return copy.deepcopy(self.report)

    def run_pipeline(self, reader=None, save=None, read=None):
        return run_quality_checked(
            'run-one', self.executors,
            save or (lambda key, value: self.checkpoints.update(
                {key: copy.deepcopy(value)})),
            read or (lambda key: copy.deepcopy(self.checkpoints[key])),
            analysis_binding=self.binding, required_domains=self.domains,
            read_analysis_evidence=reader or self.read_evidence)

    def test_complete_binds_both_receipts_to_same_report(self):
        result = self.run_pipeline()
        self.assertEqual(result.status, 'COMPLETE')
        self.assertEqual(self.reads, ['PRE_PERSISTENCE', 'POST_READBACK'])
        proof = 'analysis-evidence-sha256:' + validate_analysis_evidence(
            self.binding, self.domains, self.report)
        self.assertIn(proof, result.receipts[4].evidence_refs)
        self.assertIn(proof, result.receipts[-1].evidence_refs)
        self.assertEqual(self.checkpoints['run-one'], result.receipts)

    def test_missing_domain_stops_before_any_persistence_effect(self):
        self.report['domains'].pop()
        result = self.run_pipeline()
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.last_confirmed, 'ANALYZED')
        self.assertEqual(result.next_stage, 'PERSISTED')
        self.assertNotIn('PERSISTED', self.calls)
        self.assertNotIn('REGISTERED', self.calls)

    def test_each_missing_domain_determination_rejects_before_write(self):
        original = copy.deepcopy(self.report)
        for field in ('relevance', 'contribution', 'knowledge_impact',
                      'full_potential', 'required_action', 'questions', 'verification'):
            with self.subTest(field=field):
                self.report = copy.deepcopy(original)
                del self.report['domains'][0][field]
                self.calls = []
                self.assertEqual(self.run_pipeline().last_confirmed, 'ANALYZED')
                self.assertNotIn('PERSISTED', self.calls)

    def test_pending_required_action_cannot_hide_as_research(self):
        self.report['domains'][0]['required_action'] = dict(
            status='DEFERRED_RESEARCH', reason='Will save required connection later.',
            evidence_refs=['task:later'])
        self.report['domains'][0]['questions'] = 'Research deferred.'
        self.assertEqual(self.run_pipeline().status, 'BLOCKED')
        self.assertNotIn('PERSISTED', self.calls)

    def test_verified_required_action_needs_evidence(self):
        action = self.report['domains'][0]['required_action']
        action.update(status='VERIFIED', reason='Saved required connection.')
        self.assertEqual(self.run_pipeline().status, 'BLOCKED')
        self.assertNotIn('PERSISTED', self.calls)
        action['evidence_refs'] = ['readback:connection']
        self.assertEqual(self.run_pipeline().status, 'COMPLETE')

    def test_not_required_needs_explicit_reason(self):
        self.report['domains'][0]['required_action']['reason'] = '  '
        self.assertEqual(self.run_pipeline().status, 'BLOCKED')
        self.assertNotIn('PERSISTED', self.calls)

    def test_forged_binding_and_stale_output_text_reject_before_write(self):
        original = copy.deepcopy(self.report)
        for field in self.binding:
            with self.subTest(field=field):
                self.report = copy.deepcopy(original)
                self.report['binding'][field] = 'b' * 64 if field.endswith('sha256') else 'wrong'
                self.calls = []
                self.assertEqual(self.run_pipeline().status, 'BLOCKED')
                self.assertNotIn('PERSISTED', self.calls)
        self.report = copy.deepcopy(original)
        self.report['output_text'] += ' Altered after pinning.'
        self.calls = []
        self.assertEqual(self.run_pipeline().status, 'BLOCKED')
        self.assertNotIn('PERSISTED', self.calls)

    def test_duplicate_domain_cannot_replace_missing_domain(self):
        self.report['domains'][1] = copy.deepcopy(self.report['domains'][0])
        self.assertEqual(self.run_pipeline().status, 'BLOCKED')
        self.assertNotIn('PERSISTED', self.calls)

    def test_truthy_verification_missing_refs_and_extra_fields_rejected(self):
        original = copy.deepcopy(self.report)
        mutations = [
            lambda r: r['domains'][0]['verification'].update(status=True),
            lambda r: r['domains'][0]['verification'].update(evidence_refs=[]),
            lambda r: r['domains'][0].update(approved=True),
            lambda r: r.update(approved=True),
        ]
        for mutate in mutations:
            self.report = copy.deepcopy(original)
            mutate(self.report)
            self.calls = []
            self.assertEqual(self.run_pipeline().status, 'BLOCKED')
            self.assertNotIn('PERSISTED', self.calls)

    def test_changed_post_write_report_blocks_complete_without_replaying_write(self):
        def reader(phase):
            report = self.read_evidence(phase)
            if phase == 'POST_READBACK':
                report['domains'][0]['verification']['evidence_refs'] = ['different:review']
            return report
        result = self.run_pipeline(reader=reader)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.last_confirmed, 'REGISTERED')
        self.assertEqual(self.calls.count('PERSISTED'), 1)
        self.assertEqual(self.checkpoints['run-one'][-1].stage, 'REGISTERED')

    def test_changed_saved_text_blocks_final_completion(self):
        def reader(phase):
            report = self.read_evidence(phase)
            if phase == 'POST_READBACK':
                report['output_text'] = 'Wrong provider object.'
            return report
        result = self.run_pipeline(reader=reader)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.last_confirmed, 'REGISTERED')
        self.assertEqual(self.calls.count('PERSISTED'), 1)

    def test_reader_failure_does_not_leak_provider_details_or_write(self):
        def failed(_):
            raise RuntimeError('PRIVATE_PROVIDER_RESPONSE')
        result = self.run_pipeline(reader=failed)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertNotIn('PRIVATE_PROVIDER_RESPONSE', repr(result))
        self.assertNotIn('PERSISTED', self.calls)

    def test_failed_original_final_receipt_does_not_get_upgraded(self):
        self.executors['READBACK_VERIFIED'] = lambda _: Receipt(
            'run-one', 'READBACK_VERIFIED', False, ('failed:provider',))
        result = self.run_pipeline()
        self.assertEqual(result.status, 'INCOMPLETE')
        self.assertEqual(self.reads, ['PRE_PERSISTENCE'])

    def test_mutating_callers_plan_does_not_rebind_guard(self):
        before = copy.deepcopy(self.report)
        original = self.executors['ANALYZED']
        def analyzed(prior):
            self.binding['source_id'] = 'attacker:new-source'
            self.report['binding']['source_id'] = 'attacker:new-source'
            return original(prior)
        self.executors['ANALYZED'] = analyzed
        result = self.run_pipeline()
        self.assertEqual(result.status, 'BLOCKED')
        self.assertNotIn('PERSISTED', self.calls)
        self.assertNotEqual(before['binding'], self.report['binding'])

    def test_malformed_plan_fails_before_stage_execution(self):
        self.domains = ('Technology', 'Technology')
        with self.assertRaises(ValueError):
            self.run_pipeline()
        self.assertEqual(self.calls, [])

    def test_checkpoint_failure_still_stops_without_provider_retry(self):
        def save(key, receipts):
            if receipts[-1].stage == 'PERSISTED':
                raise OSError('PRIVATE_STORAGE_FAILURE')
            self.checkpoints[key] = copy.deepcopy(receipts)
        result = self.run_pipeline(save=save)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.last_confirmed, 'ANALYZED')
        self.assertEqual(self.calls.count('PERSISTED'), 1)
        self.assertNotIn('REGISTERED', self.calls)
        self.assertNotIn('PRIVATE_STORAGE_FAILURE', repr(result))

    def test_whitespace_claim_does_not_satisfy_domain_requirement(self):
        self.report['domains'][0]['contribution'] = '\n\t '
        self.assertEqual(self.run_pipeline().status, 'BLOCKED')
        self.assertNotIn('PERSISTED', self.calls)


if __name__ == '__main__':
    unittest.main()
