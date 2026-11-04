"""Offline checks for durable transcript processing; no provider tokens/writes."""
import os
import tempfile
import unittest

from nexus_sandbox.transcript_ingestion import (
    STAGES, TranscriptCoordinator, digest_source, source_id,
)


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.temp.name, "ingest.db")
        self.c = TranscriptCoordinator(self.path)
        self.key = self.c.receive("kokDVXUGdes", "User supplied transcript")

    def tearDown(self):
        self.c.close()
        self.temp.cleanup()

    def test_identity_and_source_digest(self):
        self.assertEqual(self.key, "youtube:kokDVXUGdes")
        self.assertEqual(self.c.get(self.key, STAGES[0]).evidence["raw_sha256"],
                         digest_source("User supplied transcript"))
        for bad in ("abc", "invalid!123", "../invalid/x"):
            with self.assertRaises(ValueError):
                source_id("youtube", bad)

    def test_idempotent_intake_but_no_silent_overwrite(self):
        self.assertEqual(self.c.receive("kokDVXUGdes", "User supplied transcript"),
                         self.key)
        with self.assertRaises(ValueError):
            self.c.receive("kokDVXUGdes", "Altered transcript")
        self.assertEqual(self.c.next_stage(self.key), "NOTION_ARCHIVE_VERIFIED")

    def test_complete_requires_external_readback_evidence(self):
        with self.assertRaises(ValueError):
            self.c.record(self.key, STAGES[1], "COMPLETE",
                          {"destination": "notion:id", "readback": "fetch:id"})
        with self.assertRaises(ValueError):
            self.c.record(self.key, STAGES[1], "COMPLETE",
                          {"destination": "notion:id"},
                          independently_read_back=True)
        self.assertEqual(self.c.next_stage(self.key), STAGES[1])

    def test_ordering_prevents_false_completion(self):
        with self.assertRaises(ValueError):
            self.c.record(self.key, STAGES[3], "COMPLETE",
                          {"destination": "cortex:mod", "readback": "search:mod"},
                          independently_read_back=True)
        self.assertEqual(self.c.receipt(self.key)["status"], "INCOMPLETE")

    def test_blocked_stage_can_retry_after_recovery(self):
        self.c.record(self.key, STAGES[1], "BLOCKED", {"error": "provider down"})
        self.assertEqual(self.c.next_stage(self.key), STAGES[1])
        self.c.record(self.key, STAGES[1], "COMPLETE",
                      {"destination": "notion:page", "readback": "fetch:page"},
                      independently_read_back=True)
        self.assertEqual(self.c.next_stage(self.key), STAGES[2])

    def test_full_sequence_and_restart(self):
        for stage in STAGES[1:]:
            self.c.record(self.key, stage, "COMPLETE",
                          {"destination": stage + ":id", "readback": stage + ":fetch"},
                          independently_read_back=True)
        self.assertIsNone(self.c.next_stage(self.key))
        self.assertEqual(self.c.receipt(self.key)["status"], "COMPLETE")
        self.c.close()
        self.c = TranscriptCoordinator(self.path)
        self.assertIsNone(self.c.next_stage(self.key))
        with self.assertRaises(ValueError):
            self.c.record(self.key, STAGES[2], "BLOCKED", {"error": "retry"})
        self.assertEqual(self.c.receipt(self.key)["status"], "COMPLETE")

    def test_retries_cannot_replace_existing_verified_evidence(self):
        self.c.record(self.key, STAGES[1], "COMPLETE",
                      {"destination": "notion:original", "readback": "fetched"},
                      independently_read_back=True)
        original = self.c.get(self.key, STAGES[1])
        item = self.c.record(self.key, STAGES[1], "COMPLETE",
                             {"destination": "notion:original", "readback": "fetched"},
                             independently_read_back=True)
        self.assertEqual(item, original)
        with self.assertRaisesRegex(ValueError, "Conflicting verified evidence"):
            self.c.record(self.key, STAGES[1], "COMPLETE",
                          {"destination": "notion:different", "readback": "other"},
                          independently_read_back=True)
        self.assertEqual(self.c.get(self.key, STAGES[1]), original)
        self.assertEqual(self.c.next_stage(self.key), STAGES[2])

    def test_invalid_noncomplete_readback_and_oversize(self):
        with self.assertRaises(ValueError):
            self.c.record(self.key, STAGES[1], "PARTIAL", {},
                          independently_read_back=True)
        with self.assertRaises(ValueError):
            self.c.record(self.key, STAGES[1], "BLOCKED", {"huge": "x"*17000})
        self.assertEqual(self.c.next_stage(self.key), STAGES[1])

    def test_independent_sources_do_not_collide(self):
        other = self.c.receive("jnjrAt6qJUA", "Other transcript")
        self.assertNotEqual(self.key, other)
        self.c.record(self.key, STAGES[1], "COMPLETE",
                      {"destination": "notion:a", "readback": "fetch:a"},
                      independently_read_back=True)
        self.assertEqual(self.c.next_stage(other), STAGES[1])


if __name__ == "__main__":
    unittest.main()
