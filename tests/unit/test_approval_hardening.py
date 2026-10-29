"""Regressions from independent inactive-bootstrap security review."""
import copy
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import approval_gate as gate
import test_approval_gate as fixtures

class HardeningTests(unittest.TestCase):
    def fixture(self):
        f = fixtures.ApprovalGateTests()
        f.setUp()
        return f

    def test_destination_string_cannot_authorize_substring(self):
        f = self.fixture()
        f.policy['destinations']['routine_write'] = 'prefixgithub:mainpostfix'
        with self.assertRaises(gate.Hold):
            f.check()

    def test_session_whitespace_cannot_create_independence(self):
        f = self.fixture()
        f.edit(0, session_id=' 1 ')
        f.edit(1, session_id='1')
        with self.assertRaises(gate.Hold):
            f.check()

    def test_evidence_paths_reject_traversal_and_ambiguous_urls(self):
        suffixes = ('../main/missing', '../../main/missing', '%2e%2e/main',
                    'file?other=revision', 'file#fragment', '', '/file')
        for suffix in suffixes:
            with self.subTest(suffix=suffix):
                f = self.fixture()
                f.edit(0, evidence=[f'https://github.com/{gate.REPOSITORY}/blob/{f.sha}/{suffix}'])
                with self.assertRaises(gate.Hold):
                    f.check()

    def test_nonstandard_json_numbers_hold(self):
        for token in ('NaN','Infinity','-Infinity'):
            with self.subTest(token=token), self.assertRaises(gate.Hold):
                gate.load_json('{"x":' + token + '}')

    def test_malformed_trust_holds_before_network(self):
        for trust in ('xx', ['a','b'], None, {'a':{},'b':{}}):
            policy = self.fixture().policy
            policy['trusted_reviewers'] = trust
            with self.subTest(trust=trust), patch.object(sys,'argv',['guard','--revision','a'*40,'--pr','84']), patch.object(gate.Path,'read_text',return_value=json.dumps(policy)), patch.object(gate,'public_get') as network, patch.object(gate,'review_list',return_value=[]), redirect_stdout(io.StringIO()):
                self.assertEqual(gate.main(),2)
                network.assert_not_called()
