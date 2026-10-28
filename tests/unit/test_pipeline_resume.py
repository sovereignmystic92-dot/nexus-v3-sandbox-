import copy
import unittest
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
from nexus_sandbox.processing_pipeline import Receipt, STAGES, run_resumable


class ResumeTests(unittest.TestCase):
    def test_fresh_process_loss_after_effect_reconciles_without_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            state = root/'checkpoint'
            effect = root/'effect'
            binding = dict(run_id='job', source_id='source', source_sha256='a'*64,
                           destination_id='destination', policy_revision='policy1',
                           code_revision='compatible1', schema_version=1)
            state.write_bytes(pickle.dumps(dict(binding=binding, receipts=(), pending=None)))
            script = '''
import os,pickle,sys
from pathlib import Path
from nexus_sandbox.processing_pipeline import *
state,effect=map(Path,sys.argv[1:])
def read(_): return pickle.loads(state.read_bytes())
def save(_,value):
    temporary=state.with_suffix('.next')
    with temporary.open('wb') as f:
        pickle.dump(value,f); f.flush(); os.fsync(f.fileno())
    os.replace(temporary,state)
    fd=os.open(state.parent,os.O_RDONLY); os.fsync(fd); os.close(fd)
binding=read(None)['binding']
def execute(stage):
    def call(prior):
        if stage==STAGES[0]:
            with effect.open('x') as f: f.write('one-effect'); f.flush(); os.fsync(f.fileno())
            os._exit(77)
        return Receipt('job',stage,True,('observed',))
    return call
def reconcile(stage,binding,prior):
    if stage==STAGES[0] and effect.read_text()=='one-effect':
        return Receipt('job',stage,True,('fresh-destination-observation',))
result=run_resumable(binding,{s:execute(s) for s in STAGES},save,read,reconcile)
assert result.status=='COMPLETE',result
'''
            env = dict(PATH=os.environ.get('PATH',''), PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src'),
                       PYTHONDONTWRITEBYTECODE='1')
            first=subprocess.run([sys.executable,'-B','-c',script,str(state),str(effect)],env=env,capture_output=True)
            self.assertEqual(first.returncode,77,first.stderr)
            self.assertEqual(pickle.loads(state.read_bytes())['pending'],STAGES[0])
            second=subprocess.run([sys.executable,'-B','-c',script,str(state),str(effect)],env=env,capture_output=True)
            self.assertEqual(second.returncode,0,second.stderr)
            third=subprocess.run([sys.executable,'-B','-c',script,str(state),str(effect)],env=env,capture_output=True)
            self.assertEqual(third.returncode,0,third.stderr)
            self.assertEqual(effect.read_text(),'one-effect')

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
    def test_saved_boolean_schema_is_not_integer_schema(self):
        self.state['binding']['schema_version'] = True
        self.assertEqual(self.run_job().status, 'BLOCKED')
        self.assertEqual(self.calls, [])
    def test_intent_readback_boolean_schema_prevents_dispatch(self):
        def changed(key,state):
            self.save(key,state)
            self.state['binding']['schema_version']=True
        self.assertEqual(self.run_job(save=changed).status,'BLOCKED')
        self.assertEqual(self.calls,[])

