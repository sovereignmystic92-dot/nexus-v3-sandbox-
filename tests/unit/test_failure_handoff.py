from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from failure_handoff import collect,InvalidEvidence


class FailureHandoffTests(unittest.TestCase):
    def setUp(self):
        self.report={'repository':'synthetic/sandbox','run_id':1,'attempt':1,'source_sha':'a'*40,
                     'status':'completed','conclusion':'failure','cases':[
                         {'test_id':'suite.test','status':'FAILED','failure_signature':'b'*64}]}
        self.packet={'repository':'synthetic/sandbox','current_sha':'a'*40,'reports':[self.report]}

    def test_failure_has_revision_bound_stable_identity_without_repair(self):
        result=collect(self.packet)
        self.assertEqual(result['findings'],collect(deepcopy(self.packet))['findings'])
        self.assertFalse(result['findings'][0]['repair_applied'])
        self.assertEqual(result['runs'][0]['disposition'],'TEST_FAILURE_OBSERVED')

    def test_duplicate_reports_and_runs_deduplicate_finding_but_keep_observations(self):
        other=dict(self.report,run_id=2)
        self.packet['reports'] += [deepcopy(self.report),other]
        result=collect(self.packet)
        self.assertEqual(len(result['findings']),1)
        self.assertEqual(len(result['findings'][0]['observations']),2)

    def test_successful_rerun_resolves_old_failure_without_losing_history(self):
        newer=deepcopy(self.report);newer.update(attempt=2,conclusion='success')
        newer['cases'][0].update(status='PASSED',failure_signature=None)
        self.packet['reports'].append(newer)
        result=collect(self.packet)
        self.assertEqual(result['findings'],[])
        self.assertEqual(result['runs'][0]['prior_failed_case_count'],1)
        self.assertEqual(result['runs'][0]['disposition'],'HEALTHY')

    def test_cancelled_pending_timeout_stale_never_propose_repair(self):
        for changes in ({'conclusion':'cancelled'},{'conclusion':'timed_out'},
                        {'status':'in_progress','conclusion':None},{'source_sha':'c'*40}):
            with self.subTest(changes=changes):
                packet=deepcopy(self.packet);packet['reports'][0].update(changes)
                self.assertEqual(collect(packet)['findings'],[])

    def test_missing_cases_or_success_with_failed_case_are_not_healthy(self):
        self.report['conclusion']='success'
        self.assertEqual(collect(self.packet)['runs'][0]['disposition'],'INCONSISTENT')
        self.report['cases']=[]
        self.assertEqual(collect(self.packet)['runs'][0]['disposition'],'INCOMPLETE_EVIDENCE')

    def test_success_with_skipped_case_is_not_clean(self):
        self.report['conclusion']='success'
        self.report['cases'][0].update(status='SKIPPED',failure_signature=None)
        self.assertEqual(collect(self.packet)['runs'][0]['disposition'],'INCOMPLETE_EVIDENCE')

    def test_conflicting_attempt_or_changed_revision_is_rejected(self):
        other=deepcopy(self.report);other['conclusion']='cancelled'
        self.packet['reports'].append(other)
        with self.assertRaises(InvalidEvidence):collect(self.packet)
        other.update(attempt=2,source_sha='c'*40)
        with self.assertRaises(InvalidEvidence):collect(self.packet)

    def test_wrong_repository_duplicate_cases_or_missing_signature_rejected(self):
        for mode in ('repository','duplicate','signature'):
            packet=deepcopy(self.packet);report=packet['reports'][0]
            if mode=='repository':report['repository']='other/repo'
            elif mode=='duplicate':report['cases']*=2
            else:report['cases'][0]['failure_signature']=None
            with self.subTest(mode=mode),self.assertRaises(InvalidEvidence):collect(packet)

    def test_newline_injection_and_extra_fields_rejected(self):
        self.report['cases'][0]['test_id']='test\n::command::'
        with self.assertRaises(InvalidEvidence):collect(self.packet)
        self.report['cases'][0]['test_id']='test'
        self.report['raw_log']='do not execute this'
        with self.assertRaises(InvalidEvidence):collect(self.packet)

    def test_empty_input_is_not_a_clean_run(self):
        self.packet['reports']=[]
        self.assertEqual(collect(self.packet)['assessment'],'NO_EVIDENCE')
