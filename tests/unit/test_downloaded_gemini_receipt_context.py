import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from nexus_sandbox.transcript_gemini_receipt import make_receipt

SPEC = importlib.util.spec_from_file_location("receipt_download_verifier",
    Path(__file__).resolve().parents[2] / "tools/verify_gemini_review_receipt.py")
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class DownloadedReceiptContextTests(unittest.TestCase):
    def test_source_bound_readback_and_negative_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            old = os.getcwd()
            try:
                os.chdir(folder)
                fixtures = Path("tests/fixtures"); fixtures.mkdir(parents=True)
                source = b"synthetic complete transcript"
                digest = hashlib.sha256(source).hexdigest()
                event = dict(schema="NEXUS_TRANSCRIPT_EVENT_V2", event_id="event-1",
                             source_ref="synthetic:1", source_sha256=digest,
                             source_byte_count=len(source), event_kind="SOURCE_READY",
                             idempotency_key=hashlib.sha256(("synthetic:1" + chr(10) + digest).encode()).hexdigest())
                (fixtures / "source.txt").write_bytes(source)
                (fixtures / "event.json").write_text(json.dumps(event))
                result = dict(status="GEMINI_REVIEW_OBTAINED_READ_ONLY", event_id="event-1",
                              source_sha256=digest, review_sha256="c"*64, model="synthetic",
                              provider_response_id="mock", notion_writes=0, cortex_writes=0,
                              durable_receipt_verified=False)
                def save():
                    Path("receipt.json").write_text(json.dumps(make_receipt(result,
                        workflow_run_id="123", workflow_run_attempt="1", commit_sha="b"*40)))
                save()
                args = ["receipt.json", "--event-file", "tests/fixtures/event.json",
                        "--source-file", "tests/fixtures/source.txt",
                        "--authorized-event-id", "event-1", "--source-ref", "synthetic:1"]
                with patch.dict(os.environ, dict(GITHUB_RUN_ID="123", GITHUB_RUN_ATTEMPT="1", GITHUB_SHA="b"*40)):
                    verifier.main(args)
                    for field, bad in (("event_id", "other"), ("source_sha256", "d"*64)):
                        with self.subTest(field=field):
                            original = result[field]; result[field] = bad; save()
                            with self.assertRaises(ValueError): verifier.main(args)
                            result[field] = original
                    save()
                    (fixtures / "source.txt").write_bytes(source + b"changed")
                    with self.assertRaises(ValueError): verifier.main(args)
                    (fixtures / "source.txt").write_bytes(source)
                    with patch.dict(os.environ, {"GITHUB_RUN_ATTEMPT": "2"}):
                        with self.assertRaises(ValueError): verifier.main(args)
                    Path("outside.txt").write_bytes(source)
                    unsafe = list(args); unsafe[4] = "outside.txt"
                    with self.assertRaises(ValueError): verifier.main(unsafe)
            finally:
                os.chdir(old)
