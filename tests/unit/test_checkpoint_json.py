import json
import unittest
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from nexus_sandbox.checkpoint_json import encode,decode,CheckpointAdapter
from nexus_sandbox.checkpoint_json import reconcile_report
from nexus_sandbox.processing_pipeline import STAGES,Receipt,run_resumable


class CheckpointTests(unittest.TestCase):
    def test_duplicate_report_and_incomplete_inventory_never_verify(self):
        record=dict(marker='job',destination='audit',payload='exact')
        args=dict(complete=True,marker='job',destination='audit',payload_sha256=sha256(b'exact').hexdigest())
        self.assertEqual(reconcile_report([record],**args),'VERIFIED_OBSERVATION')
        self.assertEqual(reconcile_report([record,record],**args),'BLOCKED_DUPLICATE')
        self.assertEqual(reconcile_report([],**args),'UNKNOWN_ABSENT')
        self.assertEqual(reconcile_report([record],**dict(args,complete=False)),'UNKNOWN')
        self.assertEqual(reconcile_report([dict(record,destination='other')],**args),'BLOCKED_MISMATCH')
        self.assertEqual(reconcile_report([dict(record,payload='changed')],**args),'BLOCKED_MISMATCH')
    def test_fresh_process_json_loss_and_reconciliation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); state=root/'checkpoint.json'; effect=root/'effect'
            state.write_text(encode(self.state,self.binding))
            script='''
import json,os,sys
from pathlib import Path
from nexus_sandbox.checkpoint_json import CheckpointAdapter
from nexus_sandbox.processing_pipeline import STAGES,Receipt,run_resumable
state,effect=map(Path,sys.argv[1:])
binding=json.loads(state.read_text())['binding']
def read(_): return state.read_text()
def write(_,text):
    tmp=state.with_suffix('.next')
    with tmp.open('w') as f: f.write(text); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,state)
    fd=os.open(state.parent,os.O_RDONLY); os.fsync(fd); os.close(fd)
adapter=CheckpointAdapter(binding,read,write)
def executor(stage):
    def call(prior):
        if stage==STAGES[0]:
            with effect.open('x') as f: f.write('one'); f.flush(); os.fsync(f.fileno())
            os._exit(77)
        return Receipt('job',stage,True,('evidence',))
    return call
def observe(stage,*_):
    if stage==STAGES[0] and effect.read_text()=='one': return Receipt('job',stage,True,('readback',))
result=run_resumable(binding,{s:executor(s) for s in STAGES},adapter.save,adapter.read,observe)
assert result.status=='COMPLETE',result
'''
            env=dict(PATH=os.environ.get('PATH',''),PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src'),PYTHONDONTWRITEBYTECODE='1')
            for expected in (77,0,0):
                result=subprocess.run([sys.executable,'-B','-c',script,str(state),str(effect)],env=env,capture_output=True)
                self.assertEqual(result.returncode,expected,result.stderr)
            self.assertEqual(effect.read_text(),'one')
    def setUp(self):
        self.binding=dict(run_id='job',source_id='source',source_sha256='a'*64,
                          destination_id='audit',policy_revision='p1',code_revision='c1',schema_version=1)
        self.state=dict(binding=self.binding,receipts=(),pending=None)
    def test_roundtrip_preserves_pipeline_types(self):
        self.state['receipts']=(Receipt('job',STAGES[0],True,('e',)),)
        self.assertEqual(decode(encode(self.state,self.binding),self.binding),self.state)
    def test_duplicate_keys_and_boolean_schema_hold(self):
        wire=encode(self.state,self.binding)
        for text in (wire.replace('"schema_version":1','"schema_version":true'),
                     wire.replace('"pending":null','"pending":null,"pending":null')):
            with self.assertRaises(ValueError): decode(text,self.binding)
    def test_wrong_revision_missing_unknown_and_bad_order_hold(self):
        wire=json.loads(encode(self.state,self.binding))
        for bad in (dict(wire,binding=dict(self.binding,code_revision='old')),
                    dict(wire,extra=1),dict(wire,pending=STAGES[2])):
            with self.assertRaises(ValueError): decode(json.dumps(bad),self.binding)
        for missing in (None,'', '{}'):
            with self.assertRaises((ValueError,TypeError)): decode(missing,self.binding)
    def test_text_transport_loss_after_effect_has_no_blind_replay(self):
        storage={'job':encode(self.state,self.binding)}
        def write(key,text): storage[key]=text
        adapter=CheckpointAdapter(self.binding,lambda k:storage[k],write)
        calls=[]
        def executor(stage):
            def apply(prior):
                calls.append(stage)
                if stage==STAGES[0]: raise TimeoutError('effect applied; acknowledgment lost')
                return Receipt('job',stage,True,('observed',))
            return apply
        executors={s:executor(s) for s in STAGES}
        self.assertEqual(run_resumable(self.binding,executors,adapter.save,adapter.read,lambda *_:None).status,'BLOCKED')
        restarted=CheckpointAdapter(self.binding,lambda k:storage[k],write)
        self.assertEqual(run_resumable(self.binding,executors,restarted.save,restarted.read,lambda *_:None).status,'BLOCKED')
        self.assertEqual(calls,[STAGES[0]])
        def observed(stage,*_): return Receipt('job',stage,True,('destination-readback',))
        self.assertEqual(run_resumable(self.binding,executors,restarted.save,restarted.read,observed).status,'COMPLETE')
        calls.clear()
        self.assertEqual(run_resumable(self.binding,executors,restarted.save,restarted.read,observed).status,'COMPLETE')
        self.assertEqual(calls,[])
