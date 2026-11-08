import unittest
from nexus_sandbox.transcript_ingestion_gate import prepare_transcript, verify_archive
from nexus_sandbox.transcript_event_replay import replay_transcript_events
from nexus_sandbox.transcript_fidelity import build_receipt, split_transcript, verify_readback


class TranscriptFidelityTests(unittest.TestCase):
    def test_preserves_unicode_and_cues(self):
        raw = "Ship — [music] 🌌\n\n" * 1000
        chunks = split_transcript(raw)
        self.assertEqual("".join(chunks), raw)
        self.assertTrue(verify_readback(raw, chunks, build_receipt(raw)))
    def test_whitespace_change_fails(self):
        raw = "A  B\n[music]"
        self.assertFalse(verify_readback(raw, [raw.replace("  ", " ")], build_receipt(raw)))
    def test_missing_chunk_fails(self):
        raw = "a" * 20000
        self.assertFalse(verify_readback(raw, split_transcript(raw)[:-1], build_receipt(raw)))
    def test_reordered_chunks_fail(self):
        raw = "a" * 12000 + "b" * 12000
        self.assertFalse(verify_readback(raw, list(reversed(split_transcript(raw))), build_receipt(raw)))
    def test_custom_chunk_size(self):
        raw = "🚀[music] " * 1500
        chunks = split_transcript(raw, 512)
        receipt = build_receipt(raw, 512)
        self.assertTrue(verify_readback(raw, chunks, receipt))
        self.assertFalse(verify_readback(raw, chunks, build_receipt(raw)))
    def test_receipt_chunk_size_tamper(self):
        raw = "abc" * 2000
        receipt = build_receipt(raw, 512)
        receipt["chunk_bytes"] = 1024
        self.assertFalse(verify_readback(raw, split_transcript(raw, 512), receipt))
    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            split_transcript("")
    def test_chunk_bounds(self):
        with self.assertRaises(ValueError):
            split_transcript("abc", 100)
    def test_receipt_tamper_fails(self):
        raw = "hello"
        receipt = build_receipt(raw)
        receipt["sha256"] = "0" * 64
        self.assertFalse(verify_readback(raw, [raw], receipt))

class TranscriptReplayTests(unittest.TestCase):
    digest = "a" * 64

    def event(self, step, event_id=None, **overrides):
        value = {"event_id": event_id or step, "step": step,
                 "source_sha256": self.digest, "authorized": True, "evidence": True}
        value.update(overrides)
        return value

    def test_replay_full_and_idempotent(self):
        steps = ["source_verified", "archive_written", "archive_readback",
                 "derived_written", "derived_readback"]
        events = [self.event(step) for step in steps]
        result = replay_transcript_events(events + [dict(events[2])], self.digest)
        self.assertEqual(result["status"], "SYNTHETIC_COMPLETE")
        self.assertIsNone(result["next_step"])
        self.assertFalse(result["provider_writes"])
        self.assertFalse(result["audit_promotion"])

    def test_partial_failure_resumes_without_promotion(self):
        events = [self.event("source_verified"), self.event("archive_written")]
        result = replay_transcript_events(events, self.digest)
        self.assertEqual(result["next_step"], "archive_readback")
        self.assertEqual(result["status"], "SYNTHETIC_INCOMPLETE")
        self.assertFalse(result["audit_promotion"])

    def test_out_of_order_rejected(self):
        with self.assertRaises(ValueError):
            replay_transcript_events([self.event("archive_written")], self.digest)

    def test_conflicting_replay_rejected(self):
        event = self.event("source_verified")
        with self.assertRaises(ValueError):
            replay_transcript_events([event, dict(event, evidence=False)], self.digest)

    def test_unauthorized_and_unverified_rejected(self):
        for key in ("authorized", "evidence"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                replay_transcript_events([self.event("source_verified", **{key: False})], self.digest)

    def test_wrong_source_rejected(self):
        with self.assertRaises(ValueError):
            replay_transcript_events([self.event("source_verified", source_sha256="b"*64)], self.digest)



class ArkshipReceiptReplayFixtureTests(unittest.TestCase):
    """Pinned real-source metadata, synthetic events; no provider operations."""
    digest = "9f0001d95812ede7be917e16989f074369050c8a29548d22f7838eb39e85c08e"
    steps = ("source_verified", "archive_written", "archive_readback",
             "derived_written", "derived_readback")

    def event(self, step):
        return {"event_id": "arkship-v1:" + step, "step": step,
                "source_sha256": self.digest, "authorized": True, "evidence": True}

    def test_verified_metadata_replay_to_completion(self):
        events = [self.event(step) for step in self.steps]
        result = replay_transcript_events(events, self.digest)
        self.assertEqual(result["status"], "SYNTHETIC_COMPLETE")
        self.assertFalse(result["provider_writes"])
        self.assertFalse(result["audit_promotion"])

    def test_resume_after_archive_readback(self):
        events = [self.event(step) for step in self.steps[:3]]
        self.assertEqual(replay_transcript_events(events, self.digest)["next_step"],
                         "derived_written")
        resumed = events + [self.event(step) for step in self.steps[3:]]
        self.assertEqual(replay_transcript_events(resumed, self.digest)["status"],
                         "SYNTHETIC_COMPLETE")

    def test_replayed_archive_write_does_not_advance(self):
        events = [self.event(step) for step in self.steps[:2]]
        result = replay_transcript_events(events + [dict(events[-1])], self.digest)
        self.assertEqual(result["completed_steps"], list(self.steps[:2]))
        self.assertEqual(result["next_step"], "archive_readback")

    def test_source_digest_mismatch_blocks(self):
        with self.assertRaises(ValueError):
            replay_transcript_events([self.event(self.steps[0])], "b" * 64)


class IngestionGateTests(unittest.TestCase):
    def test_prepare_and_verified_archive(self):
        raw = ("Relay >> [music] 🌌  " + "\\n") * 1000
        prepared = prepare_transcript(raw, 512)
        self.assertEqual("".join(prepared["chunks"]), raw)
        self.assertFalse(prepared["cortex_write_allowed"])
        result = verify_archive(prepared, list(prepared["chunks"]))
        self.assertEqual(result["state"], "ARCHIVE_VERIFIED")
        self.assertEqual(result["next_step"], "BOUNDED_DERIVED_REVIEW")
        self.assertFalse(result["cortex_write_allowed"])
        self.assertFalse(result["audit_promotion"])

    def test_archive_mismatch_blocks(self):
        prepared = prepare_transcript("A  B [music] " * 200)
        altered = [prepared["chunks"][0].replace("  ", " ", 1)]
        result = verify_archive(prepared, altered)
        self.assertEqual(result["state"], "BLOCKED_ARCHIVE_MISMATCH")
        self.assertIsNone(result["next_step"])

    def test_missing_chunk_blocks(self):
        prepared = prepare_transcript("z" * 26000)
        self.assertFalse(verify_archive(prepared, prepared["chunks"][:-1])["archive_readback_verified"])

    def test_no_provider_authorization_on_success(self):
        prepared = prepare_transcript("Mass Effect relay")
        self.assertFalse(verify_archive(prepared, prepared["chunks"])["cortex_write_allowed"])



class ArchiveResumeTests(unittest.TestCase):
    def setUp(self):
        self.p = prepare_transcript("🚀 [music] >>  A\n" * 100, 256)
        self.sha = self.p["receipt"]["sha256"]

    def observe(self, indices):
        return {"complete": True, "destination": "notion:fixture",
                "source_sha256": self.sha,
                "chunks": [{"index": i, "text": self.p["chunks"][i]} for i in indices]}

    def plan(self, observation, **kw):
        from nexus_sandbox.transcript_ingestion_gate import plan_archive_resume
        return plan_archive_resume(self.p, "notion:fixture", observation,
                                   expected_source_sha256=kw.get("sha", self.sha))

    def test_partial_resume_and_noop_retry(self):
        obs = self.observe([0])
        plan = self.plan(obs)
        self.assertEqual(plan["state"], "MISSING_CHUNKS")
        self.assertEqual([c["index"] for c in plan["missing_chunks"]],
                         list(range(1, len(self.p["chunks"]))))
        obs["chunks"].extend(plan["missing_chunks"])
        full = self.plan(obs)
        self.assertEqual(full["state"], "ARCHIVE_VERIFIED")
        self.assertEqual(full["missing_chunks"], [])
        self.assertEqual(self.plan(obs), full)
        for key in ("provider_writes_allowed", "cortex_write_allowed", "audit_promotion"):
            self.assertFalse(full[key])

    def test_unknown_write_outcome_requires_readback(self):
        result = self.plan(None)
        self.assertEqual(result["state"], "READBACK_REQUIRED")
        self.assertEqual(result["missing_chunks"], [])
        self.assertFalse(result["archive_readback_verified"])

    def test_successful_write_with_lost_reply_not_repeated(self):
        obs = self.observe(range(len(self.p["chunks"])))
        self.assertEqual(self.plan(None)["state"], "READBACK_REQUIRED")
        self.assertEqual(self.plan(obs)["missing_chunks"], [])

    def test_empty_archive_plans_all_chunks(self):
        self.assertEqual(len(self.plan(self.observe([]))["missing_chunks"]),
                         len(self.p["chunks"]))

    def test_wrong_binding_or_incomplete_readback_rejected(self):
        for field, value in (("destination", "notion:other"),
                             ("source_sha256", "0" * 64), ("complete", False),
                             ("complete", 1), ("chunks", None)):
            obs = self.observe([0])
            obs[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.plan(obs)

    def test_duplicate_conflicting_unordered_and_bad_index_rejected(self):
        for indices in ([0, 0], [1, 0]):
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                self.plan(self.observe(indices))
        for index, text in ((True, self.p["chunks"][0]), (-1, "x"),
                            (len(self.p["chunks"]), "x"), (0, "altered")):
            obs = self.observe([])
            obs["chunks"] = [{"index": index, "text": text}]
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.plan(obs)

    def test_pinned_source_cannot_be_replaced(self):
        with self.assertRaises(ValueError):
            self.plan(self.observe([]), sha="0" * 64)
        self.p["receipt"]["byte_count"] += 1
        with self.assertRaises(ValueError):
            self.plan(self.observe([]))

    def test_malformed_prepared_source_rejected(self):
        from nexus_sandbox.transcript_ingestion_gate import plan_archive_resume
        for prepared in (None, {}, dict(self.p, receipt=None),
                         dict(self.p, chunks=[])):
            with self.subTest(prepared=prepared), self.assertRaises(ValueError):
                plan_archive_resume(prepared, "notion:fixture", None,
                                    expected_source_sha256=self.sha)


    @unittest.skipUnless(__import__("sys").platform == "linux", "SIGKILL fixture requires Linux")
    def test_process_kill_before_and_after_persisted_write(self):
        """Actual owned-child kills; file-backed fake provider, no live API."""
        import json
        import os
        from pathlib import Path
        import signal
        import subprocess
        import sys
        import tempfile
        child = """
import json, os, signal, sys
from pathlib import Path
from nexus_sandbox.transcript_ingestion_gate import plan_archive_resume
root = Path(sys.argv[1])
prepared = json.loads((root / 'prepared.json').read_text())
snapshot = json.loads((root / 'provider.json').read_text())
plan = plan_archive_resume(prepared, 'notion:fixture', snapshot,
                          expected_source_sha256=prepared['receipt']['sha256'])
if sys.argv[2] == 'before':
    os.kill(os.getpid(), signal.SIGKILL)
snapshot['chunks'].extend(plan['missing_chunks'])
with (root / 'provider.json').open('w') as stream:
    json.dump(snapshot, stream)
    stream.flush()
    os.fsync(stream.fileno())
# Successful fake-provider write, lost reply and lost local process state.
os.kill(os.getpid(), signal.SIGKILL)
"""
        restart = """
import json, sys
from pathlib import Path
from nexus_sandbox.transcript_ingestion_gate import plan_archive_resume
root = Path(sys.argv[1])
prepared = json.loads((root / 'prepared.json').read_text())
snapshot = json.loads((root / 'provider.json').read_text())
print(json.dumps(plan_archive_resume(
    prepared, 'notion:fixture', snapshot,
    expected_source_sha256=prepared['receipt']['sha256'])))
"""
        # Run one missing chunk through each crash boundary in a fresh process.
        for phase in ("before", "after"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                observed = self.observe(range(len(self.p["chunks"]) - 1))
                (root / "prepared.json").write_text(json.dumps(self.p))
                (root / "provider.json").write_text(json.dumps(observed))
                env = dict(os.environ)
                env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
                killed = subprocess.run([sys.executable, "-c", child, tmp, phase],
                                        env=env, capture_output=True, timeout=10)
                self.assertEqual(killed.returncode, -signal.SIGKILL, killed.stderr)
                resumed = subprocess.run([sys.executable, "-c", restart, tmp],
                                         env=env, capture_output=True, text=True,
                                         check=True, timeout=10)
                decision = json.loads(resumed.stdout)
                if phase == "before":
                    self.assertEqual(decision["state"], "MISSING_CHUNKS")
                    self.assertEqual([c["index"] for c in decision["missing_chunks"]],
                                     [len(self.p["chunks"]) - 1])
                else:
                    self.assertEqual(decision["state"], "ARCHIVE_VERIFIED")
                    self.assertEqual(decision["missing_chunks"], [])
                    saved = json.loads((root / "provider.json").read_text())["chunks"]
                    self.assertEqual(len(saved), len(self.p["chunks"]))
                self.assertFalse(decision["provider_writes_allowed"])
                self.assertFalse(decision["audit_promotion"])


if __name__ == "__main__":
    unittest.main()
