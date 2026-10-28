import json
import unittest
from nexus_sandbox.audit_checkpoint_transport import AuditCheckpointTransport,canonical
from nexus_sandbox.checkpoint_json import encode,CheckpointAdapter
from nexus_sandbox.processing_pipeline import Receipt,STAGES,run_resumable

PAGE='00000000000000000000000000000001'


class TransportTests(unittest.TestCase):
    def test_escaped_malformed_event_and_unterminated_json_hold(self):
        initial=self.text
        for bad in ('```json\n{"event_type":"\\u004eXS_CHECKPOINT_V1","run_id":"job","run_id":"job"}\n```\n',
                    '```json\n{"event_type":"NXS_CHECKPOINT_V1"'):
            self.text=initial+bad
            with self.assertRaises(ValueError):self.transport().read('job')
        self.assertEqual(self.append_calls,0)
    def test_enrollment_cannot_import_pending_or_completed_state(self):
        for state in (dict(binding=self.binding,receipts=(),pending=STAGES[0]),
                      dict(binding=self.binding,receipts=tuple(Receipt('job',s,True,('e',)) for s in STAGES),pending=None)):
            event=dict(event_type='NXS_CHECKPOINT_V1',run_id='job',page_id=PAGE,
                       sequence=0,previous=None,checkpoint=encode(state,self.binding))
            self.text='```json\n'+canonical(event)+'\n```\n'
            with self.assertRaises(ValueError):self.transport().read('job')
    def setUp(self):
        self.binding=dict(run_id='job',source_id='s',source_sha256='a'*64,
                          destination_id=PAGE,policy_revision='p',code_revision='c',schema_version=1)
        self.initial=encode(dict(binding=self.binding,receipts=(),pending=None),self.binding)
        event=dict(event_type='NXS_CHECKPOINT_V1',run_id='job',page_id=PAGE,
                   sequence=0,previous=None,checkpoint=self.initial)
        self.text='```json\n'+canonical(event)+'\n```\n'
        self.append_calls=0
    def fetch(self,key):
        self.assertEqual(key,PAGE)
        return dict(id=PAGE,metadata={'type':'page'},text=self.text)
    def append(self,key,text):
        self.assertEqual(key,PAGE);self.append_calls+=1;self.text+=text
    def transport(self,append=None,fetch=None):
        return AuditCheckpointTransport(PAGE,self.binding,fetch or self.fetch,append or self.append)
    def test_full_pipeline_uses_enrolled_page_and_separate_readback(self):
        transport=self.transport()
        adapter=CheckpointAdapter(self.binding,transport.read,transport.save)
        calls=[]
        def execute(s):
            def action(prior):
                calls.append(s);return Receipt('job',s,True,('observed',))
            return action
        executors={s:execute(s) for s in STAGES}
        result=run_resumable(self.binding,executors,adapter.save,adapter.read,lambda *_:None)
        self.assertEqual(result.status,'COMPLETE');self.assertEqual(len(calls),7)
        self.assertEqual(self.append_calls,14)
        again=self.transport();a=CheckpointAdapter(self.binding,again.read,again.save)
        self.assertEqual(run_resumable(self.binding,executors,a.save,a.read,lambda *_:None).status,'COMPLETE')
        self.assertEqual(len(calls),7);self.assertEqual(self.append_calls,14)
        with self.assertRaises(ValueError):again.save('job',self.initial)
        self.assertEqual(self.append_calls,14)
    def test_skip_intent_and_visible_history_regression_hold(self):
        from nexus_sandbox.audit_checkpoint_transport import digest
        t=self.transport();t.read('job')
        skipped=encode(dict(binding=self.binding,receipts=(Receipt('job',STAGES[0],True,('e',)),),pending=None),self.binding)
        with self.assertRaises(ValueError):t.save('job',skipped)
        pending=encode(dict(binding=self.binding,receipts=(),pending=STAGES[0]),self.binding)
        t.save('job',pending)
        events=t._events()
        bad=dict(event_type='NXS_CHECKPOINT_V1',run_id='job',page_id=PAGE,sequence=2,
                 previous=digest(events[-1]),checkpoint=self.initial)
        self.text+='```json\n'+canonical(bad)+'\n```\n'
        with self.assertRaises(ValueError):self.transport().read('job')
    def test_missing_duplicate_or_incomplete_enrollment_holds(self):
        original=self.text
        for text in ('',original+original):
            self.text=text
            with self.assertRaises(ValueError):self.transport().read('job')
        self.text=original
        with self.assertRaises(ValueError):self.transport(fetch=lambda _:dict(self.fetch(PAGE),truncated=True)).read('job')
        self.assertEqual(self.append_calls,0)
    def test_uncertain_append_is_observed_without_duplicate(self):
        def lost(key,text):self.append(key,text);raise TimeoutError()
        t=self.transport(append=lost);t.read('job')
        changed=encode(dict(binding=self.binding,receipts=(),pending=STAGES[0]),self.binding)
        with self.assertRaises(TimeoutError):t.save('job',changed)
        with self.assertRaises(ValueError):t.save('job',changed)
        restarted=self.transport();self.assertEqual(restarted.read('job'),changed)
        restarted.save('job',changed)
        self.assertEqual(self.append_calls,1)
    def test_changed_page_wrong_binding_and_malformed_event_hold(self):
        t=self.transport();t.read('job');self.text=self.text.replace('"sequence":0','"sequence":true')
        with self.assertRaises(ValueError):t.read('job')
        with self.assertRaises(ValueError):t.save('other',self.initial)
        self.assertEqual(self.append_calls,0)
