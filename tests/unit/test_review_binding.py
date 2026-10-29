"""Synthetic record snapshots only; no actual Cortex/GitHub requests."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import review_binding as binding

class ReviewBindingTests(unittest.TestCase):
    def setUp(self):
        self.context=dict(repository=binding.REPOSITORY,pr_number=57,
            head_sha='a'*40,base_sha='b'*40,candidate_sha='c'*40,
            operation='routine_write',destination='github:main',
            request_sha256='d'*64,policy_revision='synthetic-policy-v1')
        self.source=dict(store='cortex',record_id='synthetic:review-one',record_revision='7')
        self.body='Synthetic review: findings and limitations, not approval.'
        self.evidence={'synthetic:exact-test-report':'e'*64}
        self.wire,self.digest=binding.bind(self.context,self.source,'Gemini','session-one',self.body,self.evidence)

    def check(self, **changes):
        args=dict(expected_context=self.context,expected_source=self.source,
                  expected_digest=self.digest,expected_agent='Gemini',expected_session='session-one',
                  review_body=self.body,evidence=self.evidence)
        args.update(changes)
        return binding.verify(self.wire,**args)

    def test_matching_snapshot_never_grants_approval_or_authenticates_identity(self):
        result=self.check()
        self.assertEqual(result['status'],'BOUND_UNAUTHENTICATED')
        self.assertIs(result['approval_granted'],False)
        self.assertEqual(result['identity_status'],'UNVERIFIED')

    def test_every_material_context_change_holds(self):
        for key in self.context:
            changed=dict(self.context)
            changed[key]=58 if key=='pr_number' else 'other'
            if key in ('head_sha','base_sha','candidate_sha'):changed[key]='f'*40
            if key=='request_sha256':changed[key]='f'*64
            with self.subTest(key=key),self.assertRaises(binding.Hold):
                self.check(expected_context=changed)

    def test_source_record_revision_and_store_drift_hold(self):
        for key in self.source:
            changed=dict(self.source);changed[key]='github' if key=='store' else 'other'
            with self.subTest(key=key),self.assertRaises(binding.Hold):
                self.check(expected_source=changed)

    def test_changed_review_or_evidence_hold(self):
        with self.assertRaises(binding.Hold):self.check(review_body=self.body+' changed')
        with self.assertRaises(binding.Hold):self.check(evidence={'synthetic:exact-test-report':'f'*64})

    def test_claimed_agent_or_session_cannot_substitute(self):
        with self.assertRaises(binding.Hold):self.check(expected_agent='ChatGPT')
        with self.assertRaises(binding.Hold):self.check(expected_session='session-two')

    def test_tampering_and_recomputed_digest_fail_external_anchor(self):
        packet=json.loads(self.wire);packet['session_id']='session-two'
        self.wire=binding.canonical(packet)
        with self.assertRaises(binding.Hold):self.check()
        with self.assertRaises(binding.Hold):
            self.check(expected_digest=binding.sha256(self.wire))

    def test_malformed_boolean_extra_fields_and_duplicate_json_hold(self):
        for mutation in ('boolean','authority','duplicate'):
            packet=json.loads(self.wire)
            if mutation=='boolean':packet['schema_version']=True
            if mutation=='authority':packet['authenticated_identity']='Gemini'
            wire=json.dumps(packet,sort_keys=True,separators=(',',':'))
            if mutation=='duplicate':wire=wire[:-1]+',"schema_version":1}'
            old=self.wire;self.wire=wire
            with self.subTest(mutation=mutation),self.assertRaises(binding.Hold):
                self.check(expected_digest=binding.sha256(wire))
            self.wire=old

    def test_missing_evidence_or_full_context_cannot_bind_old_research_handoff(self):
        with self.assertRaises(binding.Hold):
            binding.bind({'source_agent':'Gemini'},self.source,'Gemini','session-one',self.body,self.evidence)
        with self.assertRaises(binding.Hold):
            binding.bind(self.context,self.source,'Gemini','session-one',self.body,{})

    def test_noncanonical_size_and_nonfinite_packets_hold(self):
        for wire in (' '+self.wire,'x'*(binding.MAX_BYTES+1),self.wire[:-1]+',"extra":NaN}'):
            old=self.wire;self.wire=wire
            with self.assertRaises((binding.Hold,ValueError)):
                self.check(expected_digest=binding.sha256(wire))
            self.wire=old

    def test_verify_enforces_same_body_constraints_as_bind(self):
        for body in ('','   ','x'*65537):
            packet=json.loads(self.wire);packet['review_sha256']=binding.sha256(body)
            wire=binding.canonical(packet)
            with self.subTest(length=len(body)),self.assertRaises(binding.Hold):
                binding.verify(wire,expected_context=self.context,expected_source=self.source,
                    expected_digest=binding.sha256(wire),expected_agent='Gemini',
                    expected_session='session-one',review_body=body,evidence=self.evidence)

    def test_invalid_utf8_is_a_hold_in_both_entrypoints(self):
        bad=chr(0xd800)
        with self.assertRaises(binding.Hold):
            binding.bind(self.context,self.source,'Gemini','session-one',bad,self.evidence)
        with self.assertRaises(binding.Hold):
            binding.verify(bad,expected_context=self.context,expected_source=self.source,
                expected_digest=self.digest,expected_agent='Gemini',expected_session='session-one',
                review_body=self.body,evidence=self.evidence)
        with self.assertRaises(binding.Hold):self.check(review_body=bad)

    def test_fresh_process_can_verify_saved_snapshot_without_provider(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'snapshot.json'
            path.write_text(json.dumps(dict(wire=self.wire,digest=self.digest,
                context=self.context,source=self.source,body=self.body,evidence=self.evidence)))
            script="""import json,sys,socket
sys.path.insert(0,sys.argv[1])
import review_binding as b
socket.socket=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('No network'))
v=json.load(open(sys.argv[2]))
r=b.verify(v['wire'],expected_context=v['context'],expected_source=v['source'],
expected_digest=v['digest'],expected_agent='Gemini',expected_session='session-one',
review_body=v['body'],evidence=v['evidence'])
assert r['approval_granted'] is False and r['status']=='BOUND_UNAUTHENTICATED'
print(r['packet_sha256'])
"""
            tools=str(Path(binding.__file__).parent)
            result=subprocess.run([sys.executable,'-I','-c',script,tools,str(path)],capture_output=True,text=True,check=True)
            self.assertEqual(result.stdout.strip(),self.digest)
