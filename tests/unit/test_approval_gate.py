import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from approval_gate import (authorize, Hold, preflight, review_list, REPOSITORY,
                           load_json)


class ApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self.sha = 'a' * 40
        self.policy = {'policy_version': 'test',
                       'trusted_reviewers': {'review-a': {'provider': 'one'},
                                             'review-b': {'provider': 'two'}},
                       'destinations': {'routine_write': ['github:main']},
                       'workflows': {'tests.yml': 'offline_validation'}}
        self.pr = {'state': 'open', 'user': {'login': 'author'},
                   'head': {'sha': self.sha, 'repo': {'full_name': REPOSITORY}},
                   'base': {'ref': 'main', 'repo': {'full_name': REPOSITORY}}}
        self.reviews = []
        for number, provider in enumerate(('one', 'two'), 1):
            receipt = {'policy_version': 'test', 'revision': self.sha,
                       'operation': 'routine_write', 'destination': 'github:main',
                       'request_sha256': hashlib.sha256(json.dumps(
                           [self.sha, 'routine_write', 'github:main'],
                           separators=(',', ':')).encode()).hexdigest(),
                       'session_id': str(number), 'model': 'test-model',
                       'provider': provider, 'verdict': 'PASS', 'findings': [],
                       'prior_conclusions_seen': False, 'limitations': [],
                       'evidence': [f'https://github.com/{REPOSITORY}/actions/runs/123']}
            self.reviews.append({'id': number, 'state': 'APPROVED',
                                 'commit_id': self.sha,
                                 'user': {'login': 'review-' + ('a' if number == 1 else 'b')},
                                 'body': json.dumps(receipt)})

    def check(self):
        return authorize(self.policy, self.pr, self.reviews, self.sha,
                         'routine_write', 'github:main')

    def edit(self, index, **changes):
        value = json.loads(self.reviews[index]['body'])
        value.update(changes)
        self.reviews[index]['body'] = json.dumps(value)

    def test_two_attributable_current_revision_receipts(self):
        self.assertEqual(self.check()['verdict'], 'REVIEW_RECEIPTS_ACCEPTED')

    def test_empty_trust_and_single_reviewer_hold(self):
        self.policy['trusted_reviewers'] = {}
        with self.assertRaises(Hold): self.check()
        self.setUp()
        self.reviews.pop()
        with self.assertRaises(Hold): self.check()

    def test_author_cannot_supply_one_of_the_reviews(self):
        self.pr['user']['login'] = 'review-a'
        with self.assertRaises(Hold): self.check()

    def test_stale_sha_changed_pr_and_wrong_repository_hold(self):
        for change in ('review_sha', 'pr_sha', 'repository', 'fork', 'closed'):
            with self.subTest(change=change):
                self.setUp()
                if change == 'review_sha': self.reviews[0]['commit_id'] = 'b' * 40
                if change == 'pr_sha': self.pr['head']['sha'] = 'b' * 40
                if change == 'repository': self.pr['base']['repo']['full_name'] = 'other/repo'
                if change == 'fork': self.pr['head']['repo']['full_name'] = 'fork/repo'
                if change == 'closed': self.pr['state'] = 'closed'
                with self.assertRaises(Hold): self.check()

    def test_newer_dismissal_or_changes_requested_revokes_approval(self):
        for state in ('DISMISSED', 'CHANGES_REQUESTED', 'APPROVED'):
            with self.subTest(state=state):
                self.setUp()
                newer = dict(self.reviews[0], id=10, state=state, commit_id='b' * 40)
                self.reviews.append(newer)
                with self.assertRaises(Hold): self.check()

    def test_comment_does_not_revoke_native_approval(self):
        self.reviews.append(dict(self.reviews[0], id=10, state='COMMENTED'))
        self.assertEqual(self.check()['verdict'], 'REVIEW_RECEIPTS_ACCEPTED')

    def test_invalid_attestations_hold(self):
        for changes in ({'prior_conclusions_seen': True}, {'findings': ['unresolved']},
                        {'destination': 'notion:other'}, {'request_sha256': 'b' * 64},
                        {'provider': 'other'}, {'session_id': '2'}, {'model': ''},
                        {'evidence': []}, {'evidence': ['https://evil.example/run']},
                        {'limitations': 'none'}, {'extra': 'ignored?'}):
            with self.subTest(changes=changes):
                self.setUp()
                self.edit(0, **changes)
                with self.assertRaises(Hold): self.check()

    def test_reserved_and_unknown_operations_or_destinations_hold(self):
        for operation in ('permission_expansion', 'credential_change',
                          'destructive_action', 'unknown', 'production_deployment'):
            with self.assertRaises(Hold):
                authorize(self.policy, self.pr, self.reviews, self.sha, operation, 'github:main')

    def test_duplicate_json_fields_hold(self):
        with self.assertRaises(Hold): load_json('{"verdict":"FAIL","verdict":"PASS"}')

    def test_read_only_preflight_and_unclassified_workflow(self):
        self.assertEqual(preflight(self.policy, 'tests.yml', self.sha)['verdict'],
                         'EXEMPT_FROM_TWO_AI_APPROVAL')
        with self.assertRaises(Hold): preflight(self.policy, 'new.yml', self.sha)
        with self.assertRaises(Hold): preflight(self.policy, 'tests.yml', 'main')

    def test_pagination_collects_all_pages_and_holds_if_incomplete(self):
        calls = []
        def get(path):
            calls.append(path)
            return [{}] * (100 if len(calls) == 1 else 1)
        self.assertEqual(len(review_list(1, get)), 101)
        with self.assertRaises(Hold): review_list(1, lambda path: [{}] * 100)

