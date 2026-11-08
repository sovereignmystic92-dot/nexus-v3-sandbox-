import hashlib
import unittest
from types import SimpleNamespace
from nexus_sandbox.transcript_gemini_readonly_runner import run
from nexus_sandbox.transcript_event_preflight import SCHEMA

RAW=b"Untrusted transcript source."
REF="youtube:fixture"
SHA=hashlib.sha256(RAW).hexdigest()
EVENT={"schema":SCHEMA,"event_id":"evt-1","source_ref":REF,
       "source_sha256":SHA,"source_byte_count":len(RAW),
       "idempotency_key":hashlib.sha256((REF+chr(10)+SHA).encode()).hexdigest(),
       "event_kind":"SOURCE_READY"}

class GeminiReadOnlyRunnerTests(unittest.TestCase):
    def factory(self,calls):
        def build(*,api_key):
            calls.append(("key",bool(api_key)))
            def generate_content(**kw):
                calls.append(("invoke",kw["model"]))
                return SimpleNamespace(text="Review completed.",response_id="provider-id-1")
            return SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
        return build
    def test_real_sdk_path_with_mock_transport(self):
        calls=[]
        result=run(event=EVENT,raw_source=RAW,authorized_event_id="evt-1",
                   expected_source_ref=REF,api_key="synthetic",
                   model="gemini-3.5-flash-lite",client_factory=self.factory(calls))
        self.assertEqual(result["status"],"GEMINI_REVIEW_OBTAINED_READ_ONLY")
        self.assertEqual(result["provider_response_id"],"provider-id-1")
        self.assertFalse(result["durable_receipt_verified"])
        self.assertEqual(result["notion_writes"],0)
        self.assertEqual(len(calls),2)
    def test_bad_source_never_invokes(self):
        calls=[]
        with self.assertRaises(ValueError):
            run(event=EVENT,raw_source=b"changed",authorized_event_id="evt-1",
                expected_source_ref=REF,api_key="synthetic",
                model="gemini-3.5-flash-lite",client_factory=self.factory(calls))
        self.assertEqual(calls,[])
    def test_missing_key_never_invokes(self):
        calls=[]
        with self.assertRaises(ValueError):
            run(event=EVENT,raw_source=RAW,authorized_event_id="evt-1",
                expected_source_ref=REF,api_key="",
                model="gemini-3.5-flash-lite",client_factory=self.factory(calls))
        self.assertEqual(calls,[])
