import hashlib
import unittest
from nexus_sandbox.transcript_event_preflight import SCHEMA
from nexus_sandbox.transcript_gemini_runtime import invoke_source_bound_gemini

RAW=b"An interplanetary convoy."
REF="youtube:fixture"
SHA=hashlib.sha256(RAW).hexdigest()
EVENT={"schema":SCHEMA,"event_id":"evt-1","source_ref":REF,
       "source_sha256":SHA,"source_byte_count":len(RAW),
       "idempotency_key":hashlib.sha256((REF+chr(10)+SHA).encode()).hexdigest(),
       "event_kind":"SOURCE_READY"}

class GeminiRuntimeTests(unittest.TestCase):
    def call(self, event=EVENT, invoke=None, raw=RAW):
        return invoke_source_bound_gemini(
            event=event, raw_source=raw, authorized_event_id="evt-1",
            expected_source_ref=REF, model="gemini-3.5-flash-lite",
            invoke=invoke or (lambda m,p: ("Source needs corroboration.", "run-123")))
    def test_success(self):
        r=self.call()
        self.assertEqual(r.source_sha256,SHA)
        self.assertEqual(r.invocation_id,"run-123")
        self.assertEqual(r.review_sha256,hashlib.sha256(r.review_text.encode()).hexdigest())
    def test_prompt_contains_untrusted_data_warning(self):
        observed=[]
        self.call(invoke=lambda m,p: (observed.append(p) or "review","run"))
        self.assertIn("untrusted source data",observed[0])
        self.assertIn("interplanetary convoy",observed[0])
    def test_mismatched_source_never_calls_gemini(self):
        observed=[]
        with self.assertRaises(ValueError):
            self.call(raw=b"changed",invoke=lambda m,p: observed.append(p))
        self.assertEqual(observed,[])
    def test_empty_review_fails(self):
        with self.assertRaises(ValueError):
            self.call(invoke=lambda m,p: ("","run"))
    def test_missing_invocation_fails(self):
        with self.assertRaises(ValueError):
            self.call(invoke=lambda m,p: ("review",""))
    def test_wrong_port_shape_fails(self):
        with self.assertRaises(ValueError):
            self.call(invoke=lambda m,p: {"text":"review"})
