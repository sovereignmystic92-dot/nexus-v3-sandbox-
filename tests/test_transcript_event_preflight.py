import hashlib
import unittest
from nexus_sandbox.transcript_event_preflight import validate_event

SOURCE = b"Exact transcript.\nNo normalization.\n"
REF = "notion:fixture-1"
SHA = hashlib.sha256(SOURCE).hexdigest()
KEY = hashlib.sha256((REF + "\n" + SHA).encode()).hexdigest()

def event():
    return {"schema": "NEXUS_TRANSCRIPT_EVENT_V2", "event_id": "evt-1",
            "source_ref": REF, "source_sha256": SHA,
            "source_byte_count": len(SOURCE), "idempotency_key": KEY,
            "event_kind": "SOURCE_READY"}

def check(e, source=SOURCE, ref=REF, event_id="evt-1"):
    return validate_event(e, raw_source=source, expected_source_ref=ref,
                          authorized_event_id=event_id)

class PreflightTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(check(event())["source_sha256"], SHA)
    def test_replay_stable(self): self.assertEqual(check(event()), check(event()))
    def test_changed_source(self):
        with self.assertRaises(ValueError): check(event(), SOURCE + b"x")
    def test_wrong_ref(self):
        with self.assertRaises(ValueError): check(event(), ref="notion:other")
    def test_wrong_event(self):
        with self.assertRaises(ValueError): check(event(), event_id="evt-other")
    def test_unknown_field(self):
        e=event(); e["transcript"]="do not log"
        with self.assertRaises(ValueError): check(e)
    def test_missing_field(self):
        e=event(); del e["idempotency_key"]
        with self.assertRaises(ValueError): check(e)
    def test_invalid_key(self):
        e=event(); e["idempotency_key"]="0"*64
        with self.assertRaises(ValueError): check(e)
    def test_boolean_byte_count(self):
        e=event(); e["source_byte_count"]=True
        with self.assertRaises(ValueError): check(e)
    def test_no_source(self):
        with self.assertRaises(ValueError): check(event(), b"")
    def test_no_implicit_text_normalization(self):
        with self.assertRaises(ValueError): check(event(), SOURCE.replace(b"\n", b"\r\n"))
