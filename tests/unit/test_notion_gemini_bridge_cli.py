import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

class RealSourceCLITests(unittest.TestCase):
    def setUp(self):
        self.raw = "synthetic private source marker"
        self.reads = self.calls = 0
        self.drift = False
        self.notion = types.ModuleType("notion_csf_authenticated_source_probe")
        self.notion.PAGE_ID = "page1"
        def read(path, token):
            self.reads += 1
            return dict(id="page1", last_edited_time="changed" if self.drift and self.reads >= 5 else "rev1")
        self.notion.read_json = read
        self.notion.children = lambda *args: []
        self.notion.extract_raw = lambda blocks: self.raw
        runner = types.ModuleType("nexus_sandbox.transcript_gemini_readonly_runner")
        def run(**kwargs):
            self.calls += 1
            return dict(status="GEMINI_REVIEW_OBTAINED_READ_ONLY", event_id="e1",
                source_sha256=hashlib.sha256(kwargs["raw_source"]).hexdigest(),
                review_sha256="c"*64, model="mock", provider_response_id="mock",
                notion_writes=0, cortex_writes=0, durable_receipt_verified=False)
        runner.run = run
        path = Path(__file__).resolve().parents[2] / "tools/notion_gemini_source_bridge.py"
        spec = importlib.util.spec_from_file_location("bridge_cli_test", path)
        self.module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {self.notion.__name__: self.notion, runner.__name__: runner}):
            spec.loader.exec_module(self.module)

    def invoke(self, approved="true", revision="rev1", missing=None):
        digest = hashlib.sha256(self.raw.encode()).hexdigest()
        event = dict(schema="NEXUS_TRANSCRIPT_EVENT_V2",event_kind="SOURCE_READY",
            event_id="e1",source_ref="synthetic:1",source_sha256=digest,
            source_byte_count=len(self.raw.encode()),
            idempotency_key=hashlib.sha256(("synthetic:1"+chr(10)+digest).encode()).hexdigest())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "event.json"; path.write_text(json.dumps(event))
            env = dict(NEXUS_REAL_SOURCE_GEMINI_APPROVED=approved,
                NOTION_SANDBOX_TOKEN="mock-notion-secret",GEMINI_API_KEY="mock-gemini-secret",
                GITHUB_RUN_ID="123",GITHUB_RUN_ATTEMPT="1",GITHUB_SHA="b"*40)
            if missing:
                env.pop(missing)
            args=["bridge","--event-file",str(path),"--source-revision",revision,
                  "--event-id","e1","--source-ref","synthetic:1"]
            out,err=io.StringIO(),io.StringIO()
            with patch.dict(os.environ,env,clear=True), patch.object(sys,"argv",args), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                status=self.module.main()
            for secret in (self.raw,"mock-notion-secret","mock-gemini-secret"):
                self.assertNotIn(secret,out.getvalue()+err.getvalue())
            return status,out.getvalue(),err.getvalue()

    def test_success_emits_bound_receipt_without_content(self):
        status,out,err=self.invoke()
        self.assertEqual(status,0); self.assertEqual(self.calls,1)
        receipt=json.loads(out)
        self.assertEqual(receipt["event_id"],"e1")
        self.assertEqual(receipt["workflow_run_id"],"123")
        self.assertEqual(receipt["source_sha256"],hashlib.sha256(self.raw.encode()).hexdigest())
        self.assertFalse(receipt["durable_receipt_verified"])
    def test_http_failure_reports_stage_without_sensitive_message(self):
        import urllib.error
        def denied(*args):
            raise urllib.error.HTTPError("mock-notion-secret",403,"mock-gemini-secret",{},None)
        self.module.notion.read_json=denied
        status,out,err=self.invoke()
        self.assertEqual((status,self.calls),(2,0))
        self.assertEqual(json.loads(err)["stage"],"source_page_read")
        self.assertEqual(json.loads(err)["http_status"],403)
        self.assertEqual(out,"")
    def test_model_failure_reports_stage_without_sensitive_message(self):
        def failed(**kwargs):
            raise RuntimeError("mock-gemini-secret")
        self.module.run=failed
        status,out,err=self.invoke()
        self.assertEqual(status,2)
        self.assertEqual(json.loads(err)["stage"],"gemini_review")
        self.assertIsNone(json.loads(err)["http_status"])
        self.assertEqual(out,"")
    def test_approval_denial_precedes_source_and_model(self):
        status,out,err=self.invoke(approved="false")
        self.assertEqual((status,self.reads,self.calls),(2,0,0))
        self.assertEqual(out,"")
    def test_wrong_revision_precedes_model(self):
        status,out,err=self.invoke(revision="wrong")
        self.assertEqual(status,2); self.assertEqual(self.calls,0); self.assertEqual(out,"")
    def test_source_changes_after_model_withholds_receipt(self):
        self.drift=True
        status,out,err=self.invoke()
        self.assertEqual((status,self.calls),(2,1)); self.assertEqual(out,"")
    def test_missing_credentials_precedes_source_and_model(self):
        for key in ("NOTION_SANDBOX_TOKEN","GEMINI_API_KEY"):
            with self.subTest(key=key):
                status,out,err=self.invoke(missing=key)
                self.assertEqual((status,self.reads,self.calls),(2,0,0))
                self.assertEqual(out,"")
