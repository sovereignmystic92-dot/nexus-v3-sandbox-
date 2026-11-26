"""Synthetic recovery permits and provider ports; never live authorization."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest

import test_checkpoint_supervised_host as fixture
from nexus_sandbox.pre_dispatch_recovery import digest, recover_checkpoint_supervised
from nexus_sandbox.transcript_supervised_host import _execute_supervised, execute_supervised


class PreDispatchRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CheckpointHostTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.context['transaction_id']=self.f.base.gate['binding']['run_id']
        self.f.assignment['transaction_id']=self.f.context['transaction_id']
        self.f.fault = 'lost-reply'
        self.assertFalse(self.f.run_host(True)['transaction_complete'])
        self.f.fault = None
        self.intent = copy.deepcopy(self.f.saved)
        self.original_bytes = self.f.path.read_bytes()
        with sqlite3.connect(self.f.path) as db:
            self.original_binding = db.execute('select binding from execution').fetchone()[0]
        data = json.loads(self.original_binding)
        self.permit = dict(transaction_id=self.f.context['transaction_id'], permit_id='synthetic-permit',
            native_binding_sha256=hashlib.sha256(self.original_binding.encode()).hexdigest(),
            intent_sha256=digest(self.intent), source_sha256=data['source_sha256'],
            output_sha256=data['output_sha256'], analysis_evidence_sha256=data['analysis_evidence_sha256'],
            checkpoint_reference='synthetic-original-checkpoint@1', authority_ref='synthetic-owner-review',
            evidence_refs=['synthetic-complete-host-trace:no-provider-dispatch'],
            outcome='CONFIRMED_PRE_DISPATCH')
        self.events = []
        self.append_fault = None
        self.authorized = True

    def append(self, key, event):
        self.events.append(copy.deepcopy(event))
        if self.append_fault == event['event']:
            raise TimeoutError('synthetic retained event with lost reply')

    def recover(self, reconcile=False, permit=None, **args):
        return recover_checkpoint_supervised(context=self.f.context,
            supervised_kwargs=dict(self.f.args, allow_create=not reconcile, **args),
            original_intent=self.intent, permit=permit or self.permit,
            read_checkpoint=lambda key:copy.deepcopy(self.f.saved),
            read_recovery=lambda key:copy.deepcopy(self.events), append_recovery=self.append,
            verify_authority=lambda p:copy.deepcopy(p) if self.authorized else None,
            verify_assignment=lambda p:copy.deepcopy(self.f.assignment), reconcile_only=reconcile)

    def test_one_controlled_continuation_preserves_intent_and_binding(self):
        result = self.recover()
        self.assertTrue(result['transaction_complete'])
        self.assertFalse(result['unattended_acceptance'])
        self.assertEqual(self.intent, self.f.saved)
        self.assertEqual([e['event'] for e in self.events], ['AUTHORIZED','DISPATCH_STARTED','RECEIPT'])
        with sqlite3.connect(self.f.path) as db:
            binding,state = db.execute('select binding,state from execution').fetchone()
            self.assertEqual(binding,self.original_binding)
            self.assertEqual(state,'VERIFIED')
            self.assertEqual(db.execute('select count(*) from recovery_attempt').fetchone()[0],1)
        self.assertTrue(self.recover(True)['transaction_complete'])
        self.assertEqual(self.f.base.calls.count('cortex_create'),1)
        with self.assertRaises(ValueError): self.recover()

    def test_bad_outcome_binding_evidence_and_authority_cannot_release_intent(self):
        for field,value in [('outcome','UNCERTAIN_PROVIDER_OUTCOME'),('transaction_id','other'),
                ('native_binding_sha256','0'*64),('source_sha256','0'*64),
                ('output_sha256','0'*64),('analysis_evidence_sha256','0'*64),
                ('intent_sha256','0'*64),('evidence_refs',[])]:
            p=dict(self.permit,**{field:value})
            with self.subTest(field=field), self.assertRaises(ValueError): self.recover(permit=p)
        self.authorized=False
        with self.assertRaises(PermissionError): self.recover()
        self.assertEqual(self.f.path.read_bytes(), self.original_bytes)
        self.assertEqual(self.events,[])
        self.assertNotIn('cortex_create',self.f.base.calls)

    def test_scheduled_assignment_cannot_use_permit(self):
        self.f.assignment['mode']='SCHEDULED'
        with self.assertRaises(PermissionError): self.recover()
        self.assertEqual(self.events,[])

    def test_missing_journal_not_reconstructed(self):
        self.f.path.unlink()
        with self.assertRaises(ValueError): self.recover()
        self.assertFalse(self.f.path.exists())
        self.assertEqual(self.events,[])

    def test_existing_destination_is_not_duplicated(self):
        self.f.base.module=dict(id='unrelated',name='fixture',owner='owner',version=1,content='other')
        with self.assertRaises(ValueError): self.recover()
        self.assertEqual(self.events,[])
        self.assertNotIn('cortex_create',self.f.base.calls)

    def test_lost_authorization_reply_is_a_hold_not_another_attempt(self):
        self.append_fault='AUTHORIZED'
        with self.assertRaises(TimeoutError): self.recover()
        with self.assertRaises(PermissionError): self.recover()
        self.assertNotIn('cortex_create',self.f.base.calls)

    def test_lost_dispatch_marker_reply_consumes_permit_without_provider_create(self):
        self.append_fault='DISPATCH_STARTED'
        self.assertFalse(self.recover()['transaction_complete'])
        self.append_fault=None
        with self.assertRaises(PermissionError): self.recover()
        self.assertFalse(self.recover(True)['transaction_complete'])
        self.assertNotIn('cortex_create',self.f.base.calls)
        with sqlite3.connect(self.f.path) as db:
            self.assertEqual(db.execute('select count(*) from recovery_attempt').fetchone()[0],1)

    def test_unknown_committed_provider_effect_reconciles_readonly_once(self):
        self.f.base.fault='committed'
        self.assertFalse(self.recover()['transaction_complete'])
        self.f.base.fault=None
        self.assertTrue(self.recover(True)['transaction_complete'])
        self.assertEqual(self.f.base.calls.count('cortex_create'),1)

    def test_unknown_absent_effect_cannot_resume_even_with_different_permit(self):
        self.f.base.fault='absent'
        self.assertFalse(self.recover()['transaction_complete'])
        self.f.base.fault=None
        self.assertFalse(self.recover(True)['transaction_complete'])
        with self.assertRaises(PermissionError): self.recover(permit=dict(self.permit,permit_id='different'))
        # Exercise the native API too: changing the permit cannot consume twice.
        result=_execute_supervised(**self.f.args,recovery_authorization=dict(self.permit,permit_id='different'),
            verify_recovery=lambda p:p)
        self.assertEqual(result['handoff']['status'],'BLOCKED')
        self.assertEqual(self.f.base.calls.count('cortex_create'),1)

    def test_lost_receipt_reply_reconciles_without_reappend_or_second_create(self):
        self.append_fault='RECEIPT'
        with self.assertRaises(TimeoutError): self.recover()
        self.append_fault=None
        self.assertTrue(self.recover(True)['transaction_complete'])
        self.assertEqual(len(self.events),3)
        self.assertEqual(self.f.base.calls.count('cortex_create'),1)

    def test_source_drift_cannot_dispatch(self):
        self.f.base.fault='source'
        with self.assertRaises(ValueError): self.recover()
        self.assertNotIn('cortex_create',self.f.base.calls)

    def test_original_intent_and_gate_drift_fail_closed(self):
        self.f.saved['identity']['source_sha256']='0'*64
        with self.assertRaises(ValueError): self.recover()
        self.assertEqual(self.events,[])
        with self.assertRaises(ValueError): self.recover(output_name='other')

    def test_append_and_unbound_native_recovery_rejected(self):
        with self.assertRaises(ValueError): self.recover(update_plan={})
        with self.assertRaises(ValueError):
            _execute_supervised(**self.f.args, recovery_authorization=self.permit)
        self.assertEqual(self.f.path.read_bytes(),self.original_bytes)

    def test_public_host_cannot_resume_intent_with_a_recovery_callback(self):
        self.f.base.calls.clear()
        with self.assertRaises(TypeError):
            execute_supervised(**self.f.args, recovery_authorization=self.permit,
                               verify_recovery=lambda p: p)
        self.assertEqual(self.f.base.calls, [])
        result = execute_supervised(**self.f.args)
        self.assertEqual(result['handoff']['status'], 'BLOCKED')
        self.assertEqual(self.f.path.read_bytes(), self.original_bytes)
        self.assertNotIn('cortex_create', self.f.base.calls)

    def test_source_change_after_dispatch_marker_consumes_without_provider_create(self):
        original=self.append
        def drift(key,event):
            original(key,event)
            if event['event']=='DISPATCH_STARTED': self.f.base.fault='source'
        self.append=drift
        self.assertFalse(self.recover()['transaction_complete'])
        self.assertNotIn('cortex_create',self.f.base.calls)
        self.f.base.fault=None
        self.assertFalse(self.recover(True)['transaction_complete'])

    def test_destination_appearing_after_dispatch_marker_is_not_overwritten(self):
        original=self.append
        def drift(key,event):
            original(key,event)
            if event['event']=='DISPATCH_STARTED':
                self.f.base.module=dict(id='other',name='fixture',owner='owner',version=1,content='other')
        self.append=drift
        self.assertFalse(self.recover()['transaction_complete'])
        self.assertNotIn('cortex_create',self.f.base.calls)


    def test_native_denied_authority_leaves_journal_bytes_unchanged(self):
        result=_execute_supervised(**self.f.args,recovery_authorization=self.permit,
                                  verify_recovery=lambda p:None)
        self.assertEqual(result['handoff']['status'],'BLOCKED')
        self.assertEqual(self.f.path.read_bytes(),self.original_bytes)
        self.assertNotIn('cortex_create',self.f.base.calls)
