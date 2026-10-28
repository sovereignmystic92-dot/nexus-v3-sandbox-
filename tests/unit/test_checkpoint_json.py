import json
import unittest
from nexus_sandbox.checkpoint_json import encode,decode,CheckpointAdapter
from nexus_sandbox.processing_pipeline import STAGES,Receipt,run_resumable


class CheckpointTests(unittest.TestCase):
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
