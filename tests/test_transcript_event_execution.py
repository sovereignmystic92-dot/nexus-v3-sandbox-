import hashlib
import unittest
from nexus_sandbox.transcript_event_execution import execute_event
from nexus_sandbox.transcript_live_handoff import Observed

SOURCE=b"Exact transcript.\n"
REF="notion:page-1"
SHA=hashlib.sha256(SOURCE).hexdigest()
KEY=hashlib.sha256((REF+"\n"+SHA).encode()).hexdigest()

def event():
    return dict(schema="NEXUS_TRANSCRIPT_EVENT_V2",event_id="evt-1",
                source_ref=REF,source_sha256=SHA,source_byte_count=len(SOURCE),
                idempotency_key=KEY,event_kind="SOURCE_READY")

class EventExecutionTests(unittest.TestCase):
    def call(self, event_value=None, source=SOURCE, write=False):
        notion,cortex={},{}
        calls=[]
        def nr(k):
            calls.append("notion_read")
            return Observed(k,notion[k]) if k in notion else None
        def nw(k,v):
            calls.append("notion_write")
            notion[k]=v
        def cr(k):
            calls.append("cortex_read")
            return Observed(k,cortex[k]) if k in cortex else None
        def cw(k,v):
            calls.append("cortex_write")
            cortex[k]=v
        def run():
            return execute_event(
                event=event() if event_value is None else event_value,
                raw_source=source, authorized_event_id="evt-1",
                expected_source_ref=REF,notion_page_id="page-1",
                cortex_module_name="module-1",analysis="Analysis.",
                notion_read=nr,notion_write=nw,cortex_read=cr,cortex_write=cw,
                allow_notion_write=write,allow_cortex_write=write)
        return run,calls,notion,cortex

    def test_denied_writes(self):
        run,calls,n,c=self.call()
        self.assertEqual(run().status,"BLOCKED")
        self.assertEqual(n,{})
        self.assertEqual(c,{})
    def test_full_handoff(self):
        run,calls,n,c=self.call(write=True)
        self.assertEqual(run().status,"READBACK_MATCHED")
        self.assertEqual(n["page-1"],SOURCE.decode())
        self.assertIn(SHA,c["module-1"])
    def test_modified_bytes_never_reach_provider(self):
        run,calls,n,c=self.call(source=SOURCE+b"tampered",write=True)
        with self.assertRaises(ValueError): run()
        self.assertEqual(calls,[])
    def test_wrong_event_never_reaches_provider(self):
        e=event();e["event_id"]="unapproved"
        run,calls,n,c=self.call(event_value=e,write=True)
        with self.assertRaises(ValueError): run()
        self.assertEqual(calls,[])
    def test_invalid_utf8_never_reaches_provider(self):
        raw=b"\xff"
        e=event();e["source_sha256"]=hashlib.sha256(raw).hexdigest()
        e["source_byte_count"]=len(raw)
        e["idempotency_key"]=hashlib.sha256((REF+"\n"+e["source_sha256"]).encode()).hexdigest()
        run,calls,n,c=self.call(event_value=e,source=raw,write=True)
        with self.assertRaises(UnicodeDecodeError): run()
        self.assertEqual(calls,[])
