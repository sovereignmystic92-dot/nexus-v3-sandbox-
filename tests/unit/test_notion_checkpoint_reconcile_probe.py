"""Read-only reconciliation uses synthetic requests only."""
import importlib.util
import io
import os
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch
import test_notion_checkpoint_write_probe as existing
from nexus_sandbox.notion_checkpoint_api import RequestFailure

spec=importlib.util.spec_from_file_location('reconcile_probe',Path(__file__).resolve().parents[2]/'tools/notion_checkpoint_reconcile_probe.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.fixture=existing.WriteProbeTests();self.fixture.setUp()
    def test_absent_is_observed_without_append(self):
        result=m.reconcile(self.fixture.request,'b'*40)
        self.assertEqual(result['result'],'BLOCKED_OBSERVE_ONLY_ABSENT')
        self.assertEqual(result['writes_attempted'],0)
        self.assertEqual(result['target_run_id'],'40781386183')
        self.assertEqual(result['checkpoint_sha256'],m.TARGET_CHECKPOINT_SHA256)
        self.assertEqual(result['target_binding_source_revision'],m.TARGET_SOURCE)
        self.assertEqual(result['execution_source_revision'],'b'*40)
        self.assertEqual(result['readback_result'],'BOUNDED_ABSENCE')
        self.assertEqual(self.fixture.writes(),[])
    def test_exact_historical_checkpoint_keeps_original_binding(self):
        existing.probe.probe(self.fixture.request,m.TARGET_RUN_ID,m.TARGET_SOURCE,allow_write=True)
        before=len(self.fixture.writes())
        result=m.reconcile(self.fixture.request,'b'*40)
        self.assertEqual(result['result'],'VERIFIED_ALREADY_PRESENT')
        self.assertEqual(result['source_revision'],m.TARGET_SOURCE)
        self.assertEqual(result['execution_source_revision'],'b'*40)
        self.assertEqual(result['writes_attempted'],0)
        self.assertEqual(len(self.fixture.writes()),before)
    def test_wrong_historical_binding_is_not_accepted(self):
        existing.probe.probe(self.fixture.request,m.TARGET_RUN_ID,'a'*40,allow_write=True)
        result=m.reconcile(self.fixture.request,'b'*40)
        self.assertEqual(result['result'],'BLOCKED_BEFORE_WRITE')
        self.assertEqual(result['checkpoint_state'],'UNKNOWN')
        self.assertEqual(result['writes_attempted'],0)
        self.assertEqual(len(self.fixture.writes()),1)
    def test_independent_guard_refuses_mutation_before_callback(self):
        calls=[]
        def hostile(request,*args,**kwargs):
            self.assertFalse(kwargs['allow_write'])
            return request('PATCH','/private',{})
        with patch.object(m,'probe',hostile),self.assertRaises(ValueError):
            m.reconcile(lambda *a:calls.append(a),'b'*40)
        self.assertEqual(calls,[])
    def test_shared_observation_budget_stops_before_twelfth_get(self):
        calls=[]
        def too_many(request,*args,**kwargs):
            for _ in range(12):request('GET','/synthetic',None)
        with patch.object(m,'probe',too_many),self.assertRaises(ValueError):
            m.reconcile(lambda *a:calls.append(a),'b'*40)
        self.assertEqual(len(calls),11)
    def test_error_diagnostics_remain_sanitized_and_no_write(self):
        def denied(*args):raise RequestFailure('HTTP_ERROR',403)
        result=m.reconcile(denied,'b'*40)
        self.assertEqual(result['observation_error'],dict(category='HTTP_ERROR',http_status=403))
        self.assertEqual(result['writes_attempted'],0)
        self.assertEqual(result['checkpoint_state'],'UNKNOWN')
    def test_entrypoint_disables_client_writes_even_on_first_attempt(self):
        env=dict(GITHUB_REPOSITORY='sovereignmystic92-dot/nexus-v3-sandbox-',
            GITHUB_REF='refs/heads/main',GITHUB_EVENT_NAME='workflow_dispatch',
            NOTION_CHECKPOINT_RECONCILE_CONFIRMED='true',GITHUB_SHA='b'*40,
            GITHUB_RUN_ATTEMPT='1',NOTION_SANDBOX_TOKEN='synthetic-token')
        with patch.dict(os.environ,env,clear=True),patch.object(m,'NotionRequest') as client,patch.object(m,'reconcile',return_value={'result':'VERIFIED_ALREADY_PRESENT'}):
            with redirect_stdout(io.StringIO()):self.assertEqual(m.main(),0)
            self.assertFalse(client.call_args.kwargs['write_enabled'])
    def test_missing_confirmation_never_constructs_client(self):
        with patch.dict(os.environ,{},clear=True),patch.object(m,'NotionRequest') as client:
            with redirect_stdout(io.StringIO()):self.assertEqual(m.main(),2)
            client.assert_not_called()
    def test_invalid_execution_revision_makes_no_requests(self):
        for revision in ('bad',None,'b'*39):
            with self.assertRaises(ValueError):m.reconcile(self.fixture.request,revision)
        self.assertEqual(self.fixture.calls,[])
    def test_changed_codec_digest_cannot_be_reported_as_historical_absence(self):
        with patch.object(m,'probe',return_value=dict(writes_attempted=0,checkpoint_sha256='a'*64)),self.assertRaises(ValueError):
            m.reconcile(self.fixture.request,'b'*40)
        self.assertEqual(self.fixture.calls,[])

