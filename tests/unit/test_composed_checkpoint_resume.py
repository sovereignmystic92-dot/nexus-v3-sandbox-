"""Offline composition: saved enrollment classification and fresh-process resume.

Only temporary synthetic files are mutated. No Notion/API/network call occurs.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from nexus_sandbox.audit_checkpoint_transport import AuditCheckpointTransport, canonical
from nexus_sandbox.checkpoint_json import decode, encode
from nexus_sandbox.processing_pipeline import STAGES

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('entry',ROOT/'tools/resume_checkpoint_workflow.py')
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)

def saved():
    event=json.loads((ROOT/'tests/fixtures/saved-enrollment-40862662915.json').read_text())
    binding=dict(run_id='NXS-LIVE-CHECKPOINT-40862662915',
        source_id='github-actions:40862662915',
        source_sha256=hashlib.sha256(b'checkpoint-write-probe:40862662915').hexdigest(),
        destination_id='4018c067daa48122b82ec2ae8067d021',
        policy_revision='bounded-live-checkpoint-test-20261028-v1',
        code_revision='d55ecbe22b9a34ab0c9498cc5f7014aac20e77b2',schema_version=1)
    if (set(event)!={'event_type','run_id','page_id','sequence','previous','checkpoint'}
            or event['event_type']!='NXS_CHECKPOINT_V1' or event['sequence']!=0
            or event['previous'] is not None or event['run_id']!=binding['run_id']
            or event['page_id']!=binding['destination_id']
            or hashlib.sha256(event['checkpoint'].encode()).hexdigest()
               !='7409a0f2aae701d8d1c4cbce51426d96f455ec989f8e966ea3243696bdca17a8'):
        raise ValueError('Pinned saved enrollment mismatch')
    return binding,event['checkpoint']


RUNNER=r'''
import json,os,sys
from pathlib import Path
from nexus_sandbox.audit_checkpoint_transport import AuditCheckpointTransport
from nexus_sandbox.checkpoint_json import CheckpointAdapter
from nexus_sandbox.processing_pipeline import Receipt,STAGES,run_resumable
root=Path(sys.argv[1]);mode=sys.argv[2]
binding=json.loads((root/'binding.json').read_text())
page=root/'page.json'
def atomic(path,text):
    temp=path.with_suffix('.next')
    with temp.open('w') as stream:stream.write(text);stream.flush();os.fsync(stream.fileno())
    os.replace(temp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
def fetch(key):
    if key!=binding['destination_id']:raise ValueError('Wrong synthetic page')
    return dict(id=key,metadata={'type':'page'},text=json.loads(page.read_text())['text'],
                truncated=False,unknown_block_count=0,unknown_block_ids=[])
def append(key,text):
    if key!=binding['destination_id']:raise ValueError('Wrong synthetic page')
    observed=json.loads(page.read_text());observed['text']+=text
    atomic(page,json.dumps(observed))
transport=AuditCheckpointTransport(binding['destination_id'],binding,fetch,append)
adapter=CheckpointAdapter(binding,transport.read,transport.save)
def execute(stage):
    def call(prior):
        state=adapter.read(binding['run_id'])
        if state['pending']!=stage:raise ValueError('Intent not observed')
        with (root/'calls.log').open('a') as log:
            log.write(stage+'\n');log.flush();os.fsync(log.fileno())
        payload=dict(run_id=binding['run_id'],stage=stage,prior=len(prior))
        with (root/(stage+'.effect')).open('x') as effect:
            json.dump(payload,effect);effect.flush();os.fsync(effect.fileno())
        fd=os.open(root,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
        if mode=='crash' and stage==STAGES[3]:os._exit(77)
        return Receipt(binding['run_id'],stage,True,('synthetic-file-observed:'+stage,))
    return call
def reconcile(stage,expected,prior):
    if mode=='hold':return None
    value=json.loads((root/(stage+'.effect')).read_text())
    if value!=dict(run_id=expected['run_id'],stage=stage,prior=len(prior)):return None
    return Receipt(expected['run_id'],stage,True,('fresh-synthetic-effect-readback:'+stage,))
result=run_resumable(binding,{stage:execute(stage) for stage in STAGES},
                     adapter.save,adapter.read,reconcile)
print(json.dumps(dict(status=result.status,last=result.last_confirmed,
                      next=result.next_stage,receipts=len(result.receipts))))
sys.exit(0 if result.status=='COMPLETE' else 2)
'''


class ComposedResumeTests(unittest.TestCase):
    def test_saved_enrollment_is_initial_and_not_execution_authority(self):
        binding,text=saved();state=decode(text,binding)
        self.assertEqual(state['receipts'],());self.assertIsNone(state['pending'])
        held=entry.evaluate(binding,text,True,False)
        self.assertEqual(held['status'],'BLOCKED')
        self.assertEqual(held['next_action'],'VERIFY_CURRENT_AUTHORITY')
        # The true flag here is a synthetic host assertion, not live authorization.
        decision=entry.evaluate(binding,text,True,True)
        self.assertEqual(decision['status'],'READY_FOR_GATED_EXECUTOR')
        self.assertEqual(decision['pending'],STAGES[0])
        self.assertFalse(decision['automatic_execution'])
        self.assertEqual(decision['provider_writes'],0)

    def test_fresh_process_partial_resume_reconciles_effect_and_never_replays(self):
        original,text=saved();initial=decode(text,original)
        # Explicit separate synthetic fork; never change or advance live enrollment.
        binding=dict(original,run_id='synthetic-resume-fork',
            source_id='synthetic:saved-enrollment-snapshot',
            destination_id='00000000000000000000000000000001',
            policy_revision='synthetic-resume-only',code_revision='synthetic-resume-test')
        fork=encode(dict(binding=binding,receipts=initial['receipts'],pending=None),binding)
        event=dict(event_type='NXS_CHECKPOINT_V1',run_id=binding['run_id'],
                   page_id=binding['destination_id'],sequence=0,previous=None,checkpoint=fork)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'binding.json').write_text(json.dumps(binding))
            (root/'page.json').write_text(json.dumps({'text':chr(96)*3+'json\n'+canonical(event)+'\n'+chr(96)*3+'\n'}))
            env=dict(PATH=os.environ.get('PATH',''),PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1')
            def run(mode):
                return subprocess.run([sys.executable,'-B','-c',RUNNER,str(root),mode],
                                      env=env,capture_output=True,text=True)
            def observe():
                transport=AuditCheckpointTransport(binding['destination_id'],binding,
                    lambda _:dict(id=binding['destination_id'],metadata={'type':'page'},
                                  text=json.loads((root/'page.json').read_text())['text']),
                    lambda *_:self.fail('Parent observation must not append'))
                return transport.read(binding['run_id'])
            first=run('crash');self.assertEqual(first.returncode,77,first.stderr)
            partial=observe();state=decode(partial,binding)
            self.assertEqual(len(state['receipts']),3);self.assertEqual(state['pending'],STAGES[3])
            decision=entry.evaluate(binding,partial,True,True)
            self.assertEqual(decision['status'],'RECONCILE_ONLY')
            self.assertEqual(decision['next_action'],'OBSERVE_DESTINATION_AND_RECONCILE')
            self.assertEqual(decision['completed'],list(STAGES[:3]))
            calls=(root/'calls.log').read_text();history=(root/'page.json').read_bytes()
            hold=run('hold');self.assertEqual(hold.returncode,2,hold.stderr)
            self.assertEqual((root/'calls.log').read_text(),calls)
            self.assertEqual((root/'page.json').read_bytes(),history)
            second=run('resume');self.assertEqual(second.returncode,0,second.stderr)
            self.assertEqual((root/'calls.log').read_text().splitlines(),list(STAGES))
            complete=observe();self.assertEqual(entry.evaluate(binding,complete,True,True)['status'],'COMPLETE')
            before=(root/'page.json').read_bytes()
            third=run('resume');self.assertEqual(third.returncode,0,third.stderr)
            self.assertEqual((root/'calls.log').read_text().splitlines(),list(STAGES))
            self.assertEqual((root/'page.json').read_bytes(),before)
            self.assertEqual(len(list(root.glob('*.effect'))),7)

    def test_stale_binding_and_tampered_receipts_block_without_effects(self):
        binding,text=saved()
        for expected in (dict(binding,code_revision='stale'),dict(binding,destination_id='wrong')):
            self.assertEqual(entry.evaluate(expected,text,True,True)['status'],'BLOCKED')
        malformed=json.loads(text);malformed['pending']=STAGES[4]
        self.assertEqual(entry.evaluate(binding,json.dumps(malformed),True,True)['status'],'BLOCKED')
        self.assertEqual(entry.evaluate(binding,text,False,True)['status'],'BLOCKED')

