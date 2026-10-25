from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from verify_ci_source import verify


class CISourceTests(unittest.TestCase):
    def setUp(self):
        self.env = dict(SOURCE_EVENT='pull_request', SOURCE_REF='refs/pull/47/merge',
                        SOURCE_SHA='a'*40, PR_BASE_SHA='b'*40, PR_HEAD_SHA='c'*40,
                        PR_BASE_REF='future/stacked-target')
        self.parents = ['b'*40, 'c'*40]
        self.remote = 'b'*40

    def git(self, *args):
        if args == ('rev-parse', 'HEAD'): return 'a'*40
        if args == ('cat-file', '-p', 'HEAD'):
            return '\n'.join('parent ' + p for p in self.parents) + '\n\nmessage'
        if args[0] == 'check-ref-format':
            if '..' in args[1]: raise subprocess.CalledProcessError(1, args)
            return ''
        if args[0] == 'ls-remote': return self.remote + '\trefs/heads/' + self.env['PR_BASE_REF']
        raise AssertionError(args)

    def test_future_stacked_branch_and_stale_event_base_use_current_parents(self):
        self.env['PR_BASE_SHA'] = 'd'*40
        result = verify(self.env, self.git)
        self.assertTrue(result['merge_candidate_checked'])
        self.assertFalse(result['event_base_matches_candidate'])
        self.assertEqual(result['base_sha'], self.remote)

    def test_base_movement_or_wrong_head_rejects_old_merge_candidate(self):
        for parents in [['d'*40, 'c'*40], ['b'*40, 'd'*40], ['b'*40]]:
            self.parents = parents
            with self.subTest(parents=parents), self.assertRaises(ValueError):
                verify(self.env, self.git)

    def test_bad_remote_identity_rejected(self):
        self.remote = 'not-a-sha'
        with self.assertRaises(ValueError): verify(self.env, self.git)

    def test_invalid_branch_ref_rejected(self):
        self.env['PR_BASE_REF'] = 'bad..branch'
        with self.assertRaises(subprocess.CalledProcessError): verify(self.env, self.git)

    def test_wrong_checkout_or_event_ref_rejected(self):
        for key, value in [('SOURCE_SHA', 'd'*40), ('SOURCE_EVENT', 'pull_request_target'),
                           ('SOURCE_REF', 'refs/heads/main'), ('PR_HEAD_SHA', 'invalid')]:
            env = dict(self.env, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError): verify(env, self.git)

    def test_push_source_still_supported(self):
        env = dict(self.env, SOURCE_EVENT='push', SOURCE_REF='refs/heads/main')
        self.assertFalse(verify(env, self.git)['merge_candidate_checked'])
