"""Inactive installation only; no provider access."""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import approval_gate as gate

class BootstrapTests(unittest.TestCase):
    def test_installed_empty_trust_holds_before_network(self):
        argv = ['guard', '--revision', 'a'*40, '--pr', '57']
        with patch.object(sys, 'argv', argv), patch.object(gate, 'public_get') as network, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(gate.main(), 2)
        network.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())['verdict'], 'HOLD')

    def test_installed_policy_cannot_authorize_production(self):
        policy = gate.load_json((gate.ROOT / 'tools/approval_policy.json').read_text())
        self.assertEqual(policy['trusted_reviewers'], {})
        self.assertEqual(policy['destinations']['production_deployment'], [])
        with self.assertRaises(gate.Hold):
            gate.authorize(policy, {}, [], 'a'*40, 'production_deployment', 'production')

    def test_missing_policy_holds_without_network_or_fallback(self):
        with patch.object(sys, 'argv', ['guard','--revision','a'*40,'--pr','57','--policy','/nonexistent/bootstrap-policy']), patch.object(gate, 'public_get') as network, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(gate.main(), 2)
        network.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())['verdict'], 'HOLD')
