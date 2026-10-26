from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from ci_failure_evidence import extract_cases, retrieve
from failure_handoff import InvalidEvidence
from github_ci_logs import extract_github_cases


def stamp(text):
    return ''.join('2026-10-25T23:58:22.3003288Z ' + line + '\n'
                   for line in text.splitlines())


class GitHubLogTests(unittest.TestCase):
    def setUp(self):
        self.plain = 'test_a (suite.Tests.test_a) ... ok\n\nRan 1 test in 0.003s\n\nOK\n'

    def test_real_style_timestamp_and_method_qualified_identity(self):
        cases = extract_github_cases('\ufeff' + stamp(self.plain))
        self.assertEqual(cases, [dict(test_id='suite.Tests.test_a', status='PASSED', failure_signature=None)])

    def test_older_unittest_identity_remains_compatible(self):
        self.assertEqual(extract_cases(self.plain.replace('suite.Tests.test_a', 'suite.Tests')),
                         extract_cases(self.plain))

    def test_colors_crlf_and_workflow_noise_do_not_change_cases(self):
        text = '##[group]Run tests\n' + self.plain.replace(' ... ok', ' ... \x1b[32mok\x1b[0m') + '##[endgroup]\n'
        self.assertEqual(extract_github_cases(stamp(text).replace('\n', '\r\n')),
                         extract_github_cases(stamp(self.plain)))

    def test_missing_timestamp_control_sequences_and_oversize_hold(self):
        for text in [self.plain, stamp(self.plain) + 'unbound line\n',
                     stamp(self.plain.replace(' ... ok', ' ... \x1b[2Jok')),
                     stamp(self.plain.replace(' ... ok', ' ... ok\x00'))]:
            with self.subTest(text=text): self.assertEqual(extract_github_cases(text), [])
        with self.assertRaises(InvalidEvidence): extract_github_cases('x' * (2*1024*1024+1))

    def test_duplicate_truncated_and_unsupported_suites_hold(self):
        for text in [self.plain+self.plain, self.plain.replace('Ran 1', 'Ran 2'),
                     self.plain.replace('\nOK\n', '\n'), '{"local_test_status":"PASSED"}\n']:
            with self.subTest(text=text): self.assertEqual(extract_github_cases(stamp(text)), [])

    def test_failure_diagnostic_signature_matches_plain_log(self):
        plain = ('test_a (suite.Tests.test_a) ... FAIL\n\n'
                 '======================================================================\n'
                 'FAIL: test_a (suite.Tests.test_a)\n'
                 '----------------------------------------------------------------------\n'
                 'Traceback\nAssertionError: synthetic\n\n'
                 '----------------------------------------------------------------------\n'
                 'Ran 1 test in 0.01s\n\nFAILED (failures=1)\n')
        cases = extract_github_cases(stamp(plain))
        self.assertEqual(cases, extract_cases(plain))
        self.assertEqual(cases[0]['status'], 'FAILED')
        self.assertNotIn('AssertionError', str(cases))

    def test_injected_decoder_keeps_exact_job_binding_and_missing_log_hold(self):
        run = dict(id=1, run_attempt=1, repository={'full_name':'test/repo'},
                   head_sha='a'*40, status='completed', conclusion='success')
        job = dict(id=2, run_id=1, run_attempt=1, head_sha='a'*40, status='completed')
        def fetch(path): return {'total_count':1, 'jobs':[job]} if '/jobs?' in path else run
        result = retrieve('test/repo', 'a'*40, 1, 1, fetch,
                          lambda *args:stamp(self.plain), case_parser=extract_github_cases)
        self.assertEqual(result['handoff']['runs'][0]['disposition'], 'HEALTHY')
        job['run_attempt'] = 2
        with self.assertRaises(InvalidEvidence):
            retrieve('test/repo', 'a'*40, 1, 1, fetch,
                     lambda *args:stamp(self.plain), case_parser=extract_github_cases)
