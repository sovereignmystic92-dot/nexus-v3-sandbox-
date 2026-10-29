"""Current workflow coverage; no provider requests or credential use."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import approval_gate as gate

class WorkflowCoverageTests(unittest.TestCase):
    def policy(self):
        return gate.load_json((gate.ROOT/'tools/approval_policy.json').read_text())

    def test_new_read_only_routes_are_classified_without_write_authority(self):
        for name in ('notion-audit-access-probe.yml','notion-checkpoint-reconcile-probe.yml'):
            result=gate.preflight(self.policy(),name,'a'*40)
            self.assertEqual(result['operation'],'read_only_probe')

    def test_checkpoint_write_route_holds_without_receipt_handoff(self):
        policy=self.policy()
        self.assertEqual(policy['workflows']['notion-checkpoint-write-probe.yml'],'routine_write')
        gate.validate_policy(policy)
        with self.assertRaises(gate.Hold):
            gate.preflight(policy,'notion-checkpoint-write-probe.yml','a'*40)

    def test_all_manual_provider_routes_preflight_before_secrets(self):
        folder=gate.ROOT/'.github/workflows'
        if not folder.exists():
            self.skipTest('Isolated suite omits workflow YAML; host validates exact files')
        for name in ('gemini-smoke.yml','notion-read-probe.yml','notion-identity-probe.yml',
                     'notion-boundary-probe.yml','notion-audit-access-probe.yml',
                     'notion-checkpoint-write-probe.yml','notion-checkpoint-reconcile-probe.yml'):
            source=(folder/name).read_text()
            self.assertLess(source.index('Approval policy preflight'),source.index('${{ secrets.'))
            self.assertIn('--workflow '+name,source)
