import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import approval_gate as gate


class ContextRecheckTests(unittest.TestCase):
    def setUp(self):
        self.before = dict(state='open', user=dict(login='author'),
            head=dict(sha='a'*40, repo=dict(full_name=gate.REPOSITORY)),
            base=dict(ref='main', sha='b'*40, repo=dict(full_name=gate.REPOSITORY)))

    def test_unchanged_snapshot_is_accepted(self):
        gate.recheck_pr_context(self.before, copy.deepcopy(self.before), 'a'*40)

    def test_every_changed_binding_holds(self):
        changes = [('base','sha'), ('base','ref'), ('head','sha'),
                   ('head','repo'), ('base','repo'), ('user','login')]
        for parent, field in changes:
            with self.subTest(parent=parent,field=field):
                after=copy.deepcopy(self.before)
                after[parent][field] = dict(full_name='other/repo') if field=='repo' else 'changed'
                with self.assertRaises(gate.Hold):
                    gate.recheck_pr_context(self.before,after,'a'*40)
        after=copy.deepcopy(self.before);after['state']='closed'
        with self.assertRaises(gate.Hold):
            gate.recheck_pr_context(self.before,after,'a'*40)

    def test_missing_or_malformed_context_holds(self):
        for value in (None,{},[],dict(self.before,base=None)):
            with self.subTest(value=value),self.assertRaises(gate.Hold):
                gate.recheck_pr_context(self.before,value,'a'*40)
        for field in ('base','head','user'):
            before=copy.deepcopy(self.before);del before[field]
            with self.assertRaises(gate.Hold):
                gate.recheck_pr_context(before,before,'a'*40)
        before=copy.deepcopy(self.before);before['base']['sha']='main'
        with self.assertRaises(gate.Hold):
            gate.recheck_pr_context(before,before,'a'*40)

    def test_entrypoint_rejects_base_change_after_initial_approval(self):
        after=copy.deepcopy(self.before);after['base']['sha']='c'*40
        argv=['guard','--revision','a'*40,'--pr','57']
        policy={'policy_version':'test','trusted_reviewers':{'one':{'provider':'a'},'two':{'provider':'b'}},'destinations':{'routine_write':['github:main']},'workflows':{}}
        with patch.object(sys,'argv',argv),patch.object(gate.Path,'read_text',return_value='{}'), \
             patch.object(gate,'load_json',return_value=policy), \
             patch.object(gate,'public_get',side_effect=[self.before,after]), \
             patch.object(gate,'review_list',return_value=[]), \
             patch.object(gate,'authorize',return_value={'verdict':'REVIEW_RECEIPTS_ACCEPTED'}) as authorize, \
             patch('builtins.print') as output:
            self.assertEqual(gate.main(),2)
            authorize.assert_called_once()
            self.assertIn('HOLD',output.call_args.args[0])


if __name__=='__main__':unittest.main()

