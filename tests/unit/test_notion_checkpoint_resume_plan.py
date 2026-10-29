"""Synthetic provider-shaped tests; no network or live writes."""
import importlib.util
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch
import test_notion_checkpoint_write_probe as existing
from nexus_sandbox.notion_checkpoint_api import RequestFailure

spec=importlib.util.spec_from_file_location('plan',Path(__file__).resolve().parents[2]/'tools/notion_checkpoint_resume_plan.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ResumePlanTests(unittest.TestCase):
    def setUp(self):
        self.fixture=existing.WriteProbeTests();self.fixture.setUp()
    def seed(self,source=m.TARGET_SOURCE):
        # Synthetic fixture setup only; handoff must never advance it.
        return existing.probe.probe(self.fixture.request,m.TARGET_RUN_ID,source,allow_write=True)
    def test_verified_saved_record_hands_off_to_real_classifier_without_authority(self):
        self.assertEqual(self.seed()['result'],'VERIFIED')
        before=len(self.fixture.writes())
        with patch.object(m,'decide_resume',wraps=m.decide_resume) as classifier:
            result=m.observe_plan(self.fixture.request,'b'*40)
        self.assertEqual(result['result'],'VERIFIED_OBSERVATION_EXECUTION_BLOCKED')
        self.assertEqual(result['checkpoint_sha256'],m.TARGET_SHA256)
        self.assertEqual(result['observed_next_stage'],'SOURCE_PRESERVED')
        self.assertEqual(result['observed_completed_stages'],[])
        self.assertEqual(result['resume_decision']['status'],'BLOCKED')
        self.assertEqual(result['resume_decision']['next_action'],'VERIFY_CURRENT_AUTHORITY')
        self.assertEqual(classifier.call_args.kwargs,dict(inventory_complete=True,authority_verified=False))
        self.assertEqual(result['writes_attempted'],0)
        self.assertEqual(result['provider_writes'],0)
        self.assertEqual(result['executor_callbacks_invoked'],0)
        self.assertFalse(result['automatic_execution'])
        self.assertEqual(len(self.fixture.writes()),before)
    def test_absent_record_never_invokes_classifier_or_appends(self):
        with patch.object(m,'decide_resume') as classifier:
            result=m.observe_plan(self.fixture.request,'b'*40)
        self.assertEqual(result['result'],'BLOCKED')
        classifier.assert_not_called();self.assertEqual(self.fixture.writes(),[])
    def test_incomplete_inventory_never_invokes_classifier(self):
        self.seed()
        def incomplete(method,path,payload):
            value=self.fixture.request(method,path,payload)
            if '/children?' in path:value.update(has_more=True,next_cursor=None)
            return value
        with patch.object(m,'decide_resume') as classifier:
            result=m.observe_plan(incomplete,'b'*40)
        self.assertEqual(result['result'],'BLOCKED');classifier.assert_not_called()
        self.assertEqual(len(self.fixture.writes()),1)
    def test_source_or_digest_mismatch_never_emits_plan(self):
        self.seed('a'*40)
        self.assertEqual(m.observe_plan(self.fixture.request,'b'*40)['result'],'BLOCKED')
        self.fixture.setUp();self.seed()
        with patch.object(m,'TARGET_SHA256','a'*64):
            self.assertEqual(m.observe_plan(self.fixture.request,'b'*40)['result'],'BLOCKED')
        self.assertEqual(len(self.fixture.writes()),1)
    def test_defense_in_depth_refuses_mutation_before_callback(self):
        calls=[]
        class BadAPI:
            def __init__(self,page,request,write_enabled):
                if write_enabled:raise AssertionError('Writes enabled')
                self.fetch_page=lambda _:request('PATCH','/forbidden',{})
        with patch.object(m,'NotionCheckpointAPI',BadAPI):
            result=m.observe_plan(lambda *a:calls.append(a),'b'*40)
        self.assertEqual(result['result'],'BLOCKED');self.assertEqual(calls,[])
    def test_request_budget_stops_before_twelfth_get(self):
        calls=[]
        class BadAPI:
            def __init__(self,page,request,write_enabled):
                def fetch(_):
                    for i in range(12):request('GET','/synthetic',None)
                self.fetch_page=fetch
        with patch.object(m,'NotionCheckpointAPI',BadAPI):
            result=m.observe_plan(lambda *a:calls.append(a),'b'*40)
        self.assertEqual(result['result'],'BLOCKED');self.assertEqual(len(calls),11)
    def test_http_failure_is_observation_error_not_authority_or_execution(self):
        def denied(*_):raise RequestFailure('HTTP_ERROR',403)
        result=m.observe_plan(denied,'b'*40)
        self.assertEqual(result['result'],'BLOCKED')
        self.assertEqual(result['observation_error'],dict(category='HTTP_ERROR',http_status=403))
        self.assertIsNone(result['resume_decision']);self.assertEqual(result['writes_attempted'],0)
    def test_entrypoint_stays_read_only_and_distinguishes_task_success(self):
        env=dict(GITHUB_REPOSITORY='sovereignmystic92-dot/nexus-v3-sandbox-',
            GITHUB_REF='refs/heads/main',GITHUB_EVENT_NAME='workflow_dispatch',
            NOTION_CHECKPOINT_RECONCILE_CONFIRMED='true',GITHUB_SHA='b'*40,
            GITHUB_RUN_ATTEMPT='1',NOTION_SANDBOX_TOKEN='private-synthetic')
        with patch.dict(os.environ,env,clear=True),patch.object(m,'NotionRequest') as client,patch.object(m,'observe_plan',return_value=dict(result='VERIFIED_OBSERVATION_EXECUTION_BLOCKED')):
            output=io.StringIO()
            with redirect_stdout(output):self.assertEqual(m.main(),0)
            self.assertFalse(client.call_args.kwargs['write_enabled'])
            self.assertNotIn('private-synthetic',output.getvalue())
    def test_confirmation_or_execution_binding_missing_holds_before_provider(self):
        with patch.dict(os.environ,{},clear=True),patch.object(m,'NotionRequest') as client:
            with redirect_stdout(io.StringIO()):self.assertEqual(m.main(),2)
            client.assert_not_called()
        with self.assertRaises(ValueError):m.observe_plan(self.fixture.request,'bad')
        self.assertEqual(self.fixture.calls,[])

