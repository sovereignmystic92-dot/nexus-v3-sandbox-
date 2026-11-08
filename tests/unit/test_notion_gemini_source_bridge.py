import hashlib
import unittest
from nexus_sandbox.notion_gemini_source_bridge import review_pinned_source

class PinnedBridgeTests(unittest.TestCase):
    def setUp(self):
        self.raw=b"synthetic transcript"; digest=hashlib.sha256(self.raw).hexdigest()
        self.event=dict(schema="NEXUS_TRANSCRIPT_EVENT_V2",event_kind="SOURCE_READY",
            event_id="e1",source_ref="synthetic:1",source_sha256=digest,
            source_byte_count=len(self.raw),
            idempotency_key=hashlib.sha256(("synthetic:1"+chr(10)+digest).encode()).hexdigest())
        self.snapshot=dict(page_id="page1",revision="rev1",raw=self.raw)
        self.reads=0; self.calls=0; self.drift=0; self.bad_result=False
    def fetch(self):
        self.reads+=1
        return {**self.snapshot,"revision":"changed"} if self.reads==self.drift else dict(self.snapshot)
    def review(self,**kwargs):
        self.calls+=1
        self.assertEqual(kwargs["raw_source"],self.raw)
        return dict(status="GEMINI_REVIEW_OBTAINED_READ_ONLY",event_id="wrong" if self.bad_result else "e1",
          source_sha256=self.event["source_sha256"],review_sha256="c"*64,model="mock",
          provider_response_id="mock",notion_writes=0,cortex_writes=0,durable_receipt_verified=False)
    def run_bridge(self):
        return review_pinned_source(fetch_snapshot=self.fetch,review=self.review,event=self.event,
            expected_page_id="page1",expected_revision="rev1",authorized_event_id="e1",source_ref="synthetic:1",
            workflow_run_id="123",workflow_run_attempt="1",commit_sha="b"*40)
    def test_matching_source_one_model_call(self):
        self.assertEqual(self.run_bridge()["event_id"],"e1")
        self.assertEqual((self.reads,self.calls),(3,1))
    def test_drift_holds_without_replay(self):
        for point in (1,2,3):
            with self.subTest(point=point):
                self.reads=self.calls=0; self.drift=point
                with self.assertRaises(ValueError):self.run_bridge()
                self.assertEqual(self.calls,1 if point==3 else 0)
    def test_wrong_source_never_calls_model(self):
        self.snapshot["raw"]=b"changed"
        with self.assertRaises(ValueError):self.run_bridge()
        self.assertEqual(self.calls,0)
    def test_misbound_model_result_holds(self):
        self.bad_result=True
        with self.assertRaises(ValueError):self.run_bridge()
