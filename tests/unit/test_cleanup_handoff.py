import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.insert(0, str(TOOLS))
from cleanup_handoff import Hold, Journal
from real_container_kill_probe import process_identity, original_process_absent


class CleanupHandoffTests(unittest.TestCase):
    def test_process_incarnation_rejects_reused_pid(self):
        with tempfile.TemporaryDirectory() as folder:
            proc=Path(folder)
            (proc/'sys/kernel/random').mkdir(parents=True)
            (proc/'sys/kernel/random/boot_id').write_text('synthetic-boot')
            (proc/'123').mkdir()
            stat=proc/'123/stat'
            stat.write_text('123 (worker with spaces) '+' '.join(['S']+['0']*18+['100']))
            identity=process_identity(123,proc)
            self.assertFalse(original_process_absent(identity,123,proc))
            stat.write_text('123 (replacement) '+' '.join(['S']+['0']*18+['200']))
            self.assertTrue(original_process_absent(identity,123,proc))
            (proc/'sys/kernel/random/boot_id').write_text('different-boot')
            self.assertTrue(original_process_absent(identity,123,proc))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nexus-handoff-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / 'disposable.txt'
        self.target.write_text('synthetic')
        self.path = self.root / 'retained.sqlite'
        self.plan = {'run_id':'synthetic:one', 'source_sha':'synthetic:revision',
                     'steps':[{'action':'REMOVE','target':str(self.target),
                               'expected_state':'Owned synthetic file exists'}]}
        self.journal = Journal.create(self.path, self.plan)

    def test_intent_and_next_step_are_saved_before_action(self):
        observed = []
        def remove():
            state = Journal(self.path, self.plan).snapshot()
            observed.append(state['next_permitted_step'])
            self.assertTrue(self.target.exists())
            self.target.unlink()
        result = self.journal.execute('REMOVE', remove, lambda:not self.target.exists())
        self.assertEqual(observed, ['INSPECT_AND_RECONCILE_ONLY'])
        self.assertEqual(result['next_permitted_step'], 'COMPLETE')
        self.assertTrue(self.path.exists())

    def test_lost_acknowledgment_requires_reconciliation_without_replay(self):
        calls = []
        def lost_reply():
            calls.append('remove')
            self.target.unlink()
            raise TimeoutError('private detail')
        with self.assertRaises(TimeoutError):
            self.journal.execute('REMOVE', lost_reply, lambda:True)
        reopened = Journal(self.path, self.plan)
        with self.assertRaises(Hold):
            reopened.execute('REMOVE', lambda:calls.append('duplicate'), lambda:True)
        result = reopened.reconcile('REMOVE', lambda:not self.target.exists())
        self.assertEqual(result['next_permitted_step'], 'COMPLETE')
        self.assertEqual(calls, ['remove'])

    def test_real_process_exit_after_effect_preserves_uncertain_handoff(self):
        script = '\n'.join([
            'import sys,json,os', 'sys.path.insert(0,sys.argv[1])',
            'from cleanup_handoff import Journal', 'from pathlib import Path',
            'j=Journal(sys.argv[2],json.loads(sys.argv[3]))',
            'def remove():', '    Path(sys.argv[4]).unlink()', '    os._exit(77)',
            'j.execute("REMOVE",remove,lambda:False)'])
        child = subprocess.run([sys.executable, '-B', '-c', script, str(TOOLS),
                                str(self.path), json.dumps(self.plan), str(self.target)],
                               capture_output=True, timeout=10)
        self.assertEqual(child.returncode, 77)
        reopened = Journal(self.path, self.plan)
        self.assertEqual(reopened.snapshot()['next_permitted_step'],
                         'INSPECT_AND_RECONCILE_ONLY')
        self.assertEqual(reopened.reconcile('REMOVE', lambda:not self.target.exists())
                         ['next_permitted_step'], 'COMPLETE')

    def test_failed_observer_keeps_uncertainty(self):
        def failed():
            raise OSError('observer unavailable')
        with self.assertRaises(OSError):
            self.journal.execute('REMOVE', self.target.unlink, failed)
        self.assertEqual(Journal(self.path, self.plan).snapshot()['next_permitted_step'],
                         'INSPECT_AND_RECONCILE_ONLY')

    def test_failed_checkpoint_prevents_dispatch(self):
        def failed(_):
            raise OSError('checkpoint unavailable')
        with self.assertRaises(OSError):
            self.journal.execute('REMOVE', self.target.unlink, lambda:True, failed)
        self.assertTrue(self.target.exists())
        self.assertEqual(self.journal.snapshot()['steps'][0]['state'], 'UNCERTAIN')

    def test_failed_intent_commit_prevents_dispatch(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER unavailable BEFORE INSERT ON events "
                       "BEGIN SELECT RAISE(ABORT,'storage unavailable'); END")
        with self.assertRaises(sqlite3.DatabaseError):
            self.journal.execute('REMOVE', self.target.unlink, lambda:True)
        self.assertTrue(self.target.exists())
        state = self.journal.snapshot()
        self.assertEqual(state['steps'][0]['state'], 'PENDING')
        self.assertEqual(state['events'], [])

    def test_present_resource_requires_scope_recheck_before_explicit_retry(self):
        with self.assertRaises(Hold):
            self.journal.execute('REMOVE', lambda:None, lambda:False)
        self.assertEqual(self.journal.snapshot()['next_permitted_step'],
                         'VERIFY_OWNERSHIP_THEN_EXECUTE')
        reopened=Journal(self.path,self.plan)
        with self.assertRaises(Hold):
            reopened.execute('REMOVE', self.target.unlink, lambda:True)
        with self.assertRaises(Hold):
            reopened.execute('REMOVE', self.target.unlink, lambda:True,
                             retry_scope=lambda step:False)
        self.assertTrue(self.target.exists())
        def fresh_scope(step):
            return step['target']==str(self.target) and self.target.is_file()
        reopened.execute('REMOVE', self.target.unlink, lambda:not self.target.exists(),
                         retry_scope=fresh_scope)
        self.assertEqual(self.journal.snapshot()['steps'][0]['attempts'], 2)

    def test_completed_repeat_does_not_call_removal(self):
        self.journal.execute('REMOVE', self.target.unlink, lambda:True)
        def forbidden():
            raise AssertionError('Complete operation repeated')
        self.assertEqual(self.journal.execute('REMOVE', forbidden, forbidden)
                         ['next_permitted_step'], 'COMPLETE')

    def test_wrong_plan_and_missing_journal_hold(self):
        with self.assertRaises(Hold):
            Journal(self.path, dict(self.plan, run_id='another-run'))
        missing = self.root / 'missing.sqlite'
        with self.assertRaises(sqlite3.OperationalError):
            Journal(missing, self.plan)
        self.assertFalse(missing.exists())

    def test_corrupted_state_cannot_claim_completion(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE steps SET state='VERIFIED'")
        with self.assertRaises(Hold):
            Journal(self.path, self.plan)

    def test_step_order_is_enforced_and_last_confirmed_is_visible(self):
        path = self.root / 'ordered.sqlite'
        plan = dict(self.plan, steps=[{'action':'A','target':'fixture-a',
                                      'expected_state':'Synthetic A pending'},
                                     {'action':'B','target':'fixture-b',
                                      'expected_state':'Synthetic B pending'}])
        journal = Journal.create(path, plan)
        with self.assertRaises(Hold):
            journal.execute('B', lambda:None, lambda:True)
        result = journal.execute('A', lambda:None, lambda:True)
        self.assertEqual(result['last_verified'], ['A'])
        self.assertEqual(result['next_action'], 'B')

    def test_non_boolean_observation_does_not_confirm(self):
        with self.assertRaises(Hold):
            self.journal.execute('REMOVE', lambda:None, lambda:1)
        self.assertEqual(self.journal.snapshot()['steps'][0]['state'], 'UNCERTAIN')

    def test_existing_journal_cannot_be_reinitialized(self):
        with self.assertRaises(FileExistsError):
            Journal.create(self.path, self.plan)


if __name__ == '__main__':
    unittest.main()
