import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import declared_review_gate as gate
import review_binding as binding

class DeclaredTests(unittest.TestCase):
    def setUp(self):
        self.context=dict(repository=binding.REPOSITORY,pr_number=57,head_sha='a'*40,
            base_sha='b'*40,candidate_sha='c'*40,operation='routine_write',
            destination='github:main',request_sha256='d'*64,policy_revision='synthetic')
        self.rows=[]
        for i,agent in enumerate(('ChatGPT','Gemini')):
            source=dict(store='cortex',record_id='synthetic:'+str(i),record_revision='1')
            session='review-'+str(i)
            body=json.dumps(dict(author_session='author',reviewer_agent=agent,
                reviewer_session=session,verdict='PASS',findings=[],
                initial_findings_recorded_independently=True,exposure_disclosure='No prior initial conclusions seen'))
            evidence={'synthetic:test-report':'e'*64}
            wire,digest=binding.bind(self.context,source,agent,session,body,evidence)
            self.rows.append(dict(wire=wire,digest=digest,source=source,agent=agent,
                                  session=session,body=body,evidence=evidence))
    def check(self,**kw):
        args=dict(context=self.context,author_session='author',owner_decision=gate.OWNER_DECISION)
        args.update(kw)
        return gate.authorize_declared(self.rows,**args)
    def rebind(self,row):
        row['wire'],row['digest']=binding.bind(self.context,row['source'],row['agent'],
            row['session'],row['body'],row['evidence'])
    def test_chat_and_gemini_declared_ownership_pass_without_authentication_claim(self):
        r=self.check()
        self.assertEqual(r['verdict'],'OWNER_ACCEPTED_DECLARED_REVIEWS')
        self.assertFalse(r['dispatch_authorized'])
        self.assertEqual(r['identity_status'],'SELF_DECLARED_NOT_PROVIDER_AUTHENTICATED')
    def test_missing_duplicate_or_self_review_holds(self):
        old=copy.deepcopy(self.rows)
        for rows in ([],old[:1],[old[0],old[0]]):
            self.rows=rows
            with self.assertRaises(gate.Hold):self.check()
        self.rows=old
        with self.assertRaises(gate.Hold):self.check(author_session='review-0')
    def test_stale_binding_and_missing_owner_decision_hold(self):
        c=dict(self.context,head_sha='f'*40)
        with self.assertRaises(gate.Hold):self.check(context=c)
        with self.assertRaises(gate.Hold):self.check(owner_decision='other')
    def test_unresolved_or_false_independence_or_mislabeled_agent_hold(self):
        original=copy.deepcopy(self.rows)
        for key,value in [('findings',['open']),('verdict','PARTIAL'),
                          ('initial_findings_recorded_independently',False),
                          ('reviewer_agent','ChatGPT'),('exposure_disclosure','')]:
            self.rows=copy.deepcopy(original);r=self.rows[1]
            body=json.loads(r['body']);body[key]=value;r['body']=json.dumps(body);self.rebind(r)
            with self.subTest(key=key),self.assertRaises(gate.Hold):self.check()
    def test_changed_evidence_or_non_sandbox_destination_hold(self):
        self.rows[0]['evidence']={'synthetic:test-report':'f'*64}
        with self.assertRaises(gate.Hold):self.check()
        c=dict(self.context,destination='production')
        with self.assertRaises(gate.Hold):self.check(context=c)
