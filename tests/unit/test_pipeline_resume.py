import copy
import unittest
from nexus_sandbox.processing_pipeline import Receipt, STAGES, run_resumable


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.binding = dict(run_id='job', source_id='source', source_sha256='a'*64,
                            destination_id='destination', policy_revision='policy1',
                            code_revision='compatible1', schema_version=1)
        self.state = dict(binding=self.binding.copy(), receipts=(), pending=None)
        self.calls = []
        self.executors = {s: self.executor(s) for s in STAGES}
    def executor(self, s):
        def execute(prior):
            self.assertEqual(self.state['pending'], s)
            self.calls.append(s)
            return Receipt('job', s, True, ('observed:'+s,))
        return execute
    def save(self, key, state):
        self.state = copy.deepcopy(state)
    def run_job(self, reconcile=lambda *_:None, save=None):
        return run_resumable(self.binding, self.executors, save or self.save,
                             lambda _:copy.deepcopy(self.state), reconcile)
    def test_completed_repeat_has_zero_callbacks(self):
        self.assertEqual(self.run_job().status, 'COMPLETE')
        self.calls.clear()
        self.assertEqual(self.run_job().status, 'COMPLETE')
        self.assertEqual(self.calls, [])
    def test_partial_prefix_runs_only_remainder(self):
        self.state['receipts'] = tuple(Receipt('job', s, True, ('e',)) for s in STAGES[:4])
        self.assertEqual(self.run_job().status, 'COMPLETE')
        self.assertEqual(self.calls, list(STAGES[4:]))
    def test_missing_misbound_and_reordered_hold(self):
        for bad in (None, dict(self.state, binding=dict(self.binding, policy_revision='old')),
                    dict(self.state, receipts=(Receipt('job', STAGES[1], True, ('e',)),)),
                    dict(self.state, pending=STAGES[2])):
            self.state=bad
            self.assertEqual(self.run_job().status, 'BLOCKED')
            self.assertEqual(self.calls, [])
    def test_lost_ack_never_reexecutes(self):
        def lost(_):
            self.calls.append('effect')
            raise TimeoutError()
        self.executors[STAGES[0]]=lost
        self.assertEqual(self.run_job().status, 'BLOCKED')
        self.assertEqual(self.run_job().status, 'BLOCKED')
        self.assertEqual(self.calls, ['effect'])
        def observe(stage, binding, prior):
            return Receipt('job', stage, True, ('destination-readback',))
        self.assertEqual(self.run_job(observe).status, 'COMPLETE')
        self.assertEqual(self.calls.count('effect'), 1)
    def test_failed_intent_prevents_execution(self):
        def failed(*_): raise OSError()
        self.assertEqual(self.run_job(save=failed).status, 'BLOCKED')
        self.assertEqual(self.calls, [])

