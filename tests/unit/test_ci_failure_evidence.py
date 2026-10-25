from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from ci_failure_evidence import retrieve, extract_cases
from failure_handoff import InvalidEvidence


class CIEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.run = dict(id=12, run_attempt=2, repository={'full_name':'test/repo'},
                        head_sha='a'*40, status='completed', conclusion='success')
        self.job = dict(id=34, run_id=12, run_attempt=2, head_sha='a'*40, status='completed')
        self.log = 'test_a (suite.Tests) ... ok\n\nRan 1 test in 0.01s\n\nOK\n'
    def fetch(self, path):
        return {'total_count':1,'jobs':[deepcopy(self.job)]} if '/jobs?' in path else deepcopy(self.run)
    def call(self, logs=True):
        return retrieve('test/repo','a'*40,12,2,self.fetch,(lambda *args:self.log) if logs else None)
    def test_success_requires_cases(self):
        self.assertEqual(self.call()['handoff']['runs'][0]['disposition'],'HEALTHY')
        self.assertEqual(self.call(False)['handoff']['runs'][0]['disposition'],'INCOMPLETE_EVIDENCE')
    def test_failure_extracts_diagnostic_hash_without_raw_log(self):
        self.run['conclusion']='failure'
        self.log='test_a (suite.Tests) ... FAIL\n\n======================================================================\nFAIL: test_a (suite.Tests)\n----------------------------------------------------------------------\nTraceback\nAssertionError: wrong\n\n----------------------------------------------------------------------\nRan 1 test in 0.01s\n\nFAILED (failures=1)\n'
        result=self.call()
        self.assertEqual(len(result['handoff']['findings']),1)
        self.assertNotIn('AssertionError',str(result))
    def test_stale_run_never_suggests_repair(self):
        self.run['head_sha']='b'*40;self.job['head_sha']='b'*40
        self.assertEqual(self.call()['handoff']['runs'][0]['disposition'],'STALE_REVISION')
    def test_wrong_run_attempt_repository_or_job_binding_rejected(self):
        for obj,key,value in [(self.run,'run_attempt',1),(self.job,'run_id',99),(self.job,'head_sha','b'*40),
                              (self.run,'repository',{'full_name':'other/repo'})]:
            old=obj[key];obj[key]=value
            with self.assertRaises(InvalidEvidence):self.call()
            obj[key]=old
    def test_incomplete_duplicate_and_missing_diagnostic_logs_hold(self):
        for log in [self.log.replace('Ran 1','Ran 2'),self.log+self.log,
                    'test_a (suite.Tests) ... FAIL\nRan 1 test in 0.01s\nFAILED (failures=1)\n']:
            self.assertEqual(extract_cases(log),[])
    def test_missing_log_is_incomplete(self):
        result=retrieve('test/repo','a'*40,12,2,self.fetch,lambda *args:None)
        self.assertFalse(result['provenance']['case_evidence_complete'])
    def test_inventory_truncation_rejected(self):
        def fetch(path):
            return {'total_count':2,'jobs':[self.job]} if '/jobs?' in path else self.run
        with self.assertRaises(InvalidEvidence):retrieve('test/repo','a'*40,12,2,fetch)
    def test_oversized_or_command_shaped_logs_not_executed(self):
        self.assertEqual(extract_cases('$(touch /tmp/should-not-exist)'),[])
        with self.assertRaises(InvalidEvidence):extract_cases('x'*(2*1024*1024+1))
