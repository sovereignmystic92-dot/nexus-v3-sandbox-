import hashlib
import unittest
from nexus_sandbox.transcript_event_preflight import SCHEMA
from nexus_sandbox.transcript_gemini_review import GeminiReview
from nexus_sandbox.transcript_reviewed_execution import execute_reviewed_event
from nexus_sandbox.transcript_live_handoff import Observed

RAW=b"Source transcript unchanged."
SHA=hashlib.sha256(RAW).hexdigest()
REF="notion:fixture"
TEXT="Gemini review, source bound."
EVENT={"schema":SCHEMA,"event_id":"authorized-1","source_ref":REF,
       "source_sha256":SHA,"source_byte_count":len(RAW),
       "idempotency_key":hashlib.sha256((REF+"\\n"+SHA).encode()).hexdigest(),
       "event_kind":"SOURCE_READY"}

def review(**kwargs):
    values=dict(source_sha256=SHA,source_ref=REF,model="gemini-test",
                review_text=TEXT,review_sha256=hashlib.sha256(TEXT.encode()).hexdigest(),
                invocation_id="run-1")
    values.update(kwargs)
    return GeminiReview(**values)

class ReviewedExecutionTests(unittest.TestCase):
    def call(self, candidate):
        calls=[]
        notion={"page-1":RAW.decode()}
        cortex={}
        def nread(k):
            calls.append("notion_read")
            return Observed(k,notion[k]) if k in notion else None
        def cread(k):
            calls.append("cortex_read")
            return Observed(k,cortex[k]) if k in cortex else None
        def cwrite(k,v):
            calls.append("cortex_write")
            cortex[k]=v
        def nwrite(k,v):
            calls.append("notion_write")
            notion[k]=v
        result=execute_reviewed_event(
            event=EVENT,raw_source=RAW,authorized_event_id="authorized-1",
            expected_source_ref=REF,gemini_review=candidate,
            notion_page_id="page-1",cortex_module_name="module-1",
            notion_read=nread,notion_write=nwrite,
            cortex_read=cread,cortex_write=cwrite,
            allow_cortex_write=True)
        return result,calls,cortex

    def test_reviewed_handoff(self):
        (handoff,evidence),calls,cortex=self.call(review())
        self.assertEqual(handoff.status,"READBACK_MATCHED")
        self.assertEqual(evidence["invocation_id"],"run-1")
        self.assertIn("Gemini review",cortex["module-1"])

    def test_wrong_source_rejected_before_provider_calls(self):
        calls=[]
        with self.assertRaises(ValueError):
            self.call(review(source_sha256="b"*64))

    def test_modified_review_rejected(self):
        with self.assertRaises(ValueError):
            self.call(review(review_text="tampered"))

    def test_missing_invocation_rejected(self):
        with self.assertRaises(ValueError):
            self.call(review(invocation_id=""))

    def test_wrong_reference_rejected(self):
        with self.assertRaises(ValueError):
            self.call(review(source_ref="notion:other"))
