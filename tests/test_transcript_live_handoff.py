import unittest
from nexus_sandbox.transcript_live_handoff import Observed, run_handoff


class LiveHandoffTests(unittest.TestCase):
    def ports(self):
        notion, cortex = {}, {}
        return notion, cortex

    def call(self, notion, cortex, **kw):
        return run_handoff(
            transcript="Full transcript.", notion_page_id="notion-1",
            cortex_module_name="module-1", analysis="Attributed analysis.",
            notion_read=lambda k: Observed(k, notion[k]) if k in notion else None,
            notion_write=lambda k, v: notion.__setitem__(k, v),
            cortex_read=lambda k: Observed(k, cortex[k]) if k in cortex else None,
            cortex_write=lambda k, v: cortex.__setitem__(k, v),
            **kw)

    def test_missing_grants_do_not_write(self):
        n, c = self.ports()
        r = self.call(n, c)
        self.assertEqual(r.status, "BLOCKED")
        self.assertEqual((n, c), ({}, {}))

    def test_full_roundtrip_and_idempotent_read(self):
        n, c = self.ports()
        r = self.call(n, c, allow_notion_write=True, allow_cortex_write=True)
        self.assertEqual(r.status, "READBACK_MATCHED")
        self.assertIn(r.source_sha256, c["module-1"])
        self.assertEqual(self.call(n, c).status, "READBACK_MATCHED")

    def test_never_overwrites_conflicting_source(self):
        n, c = {"notion-1": "other transcript"}, {}
        r = self.call(n, c, allow_notion_write=True, allow_cortex_write=True)
        self.assertEqual(r.next_action, "NOTION_CONFLICT_RECONCILE_NO_OVERWRITE")
        self.assertEqual(n["notion-1"], "other transcript")
        self.assertFalse(c)

    def test_never_overwrites_conflicting_cortex(self):
        n, c = {"notion-1": "Full transcript."}, {"module-1": "different"}
        r = self.call(n, c, allow_cortex_write=True)
        self.assertEqual(r.next_action, "CORTEX_CONFLICT_RECONCILE_NO_OVERWRITE")
        self.assertEqual(c["module-1"], "different")

    def test_uncertain_write_stops(self):
        n, c = {}, {}
        def uncertain(k, v):
            n[k] = v
            raise TimeoutError("ack lost")
        r = run_handoff(
            transcript="Full transcript.", notion_page_id="notion-1",
            cortex_module_name="module-1", analysis="Attributed analysis.",
            notion_read=lambda k: Observed(k, n[k]) if k in n else None,
            notion_write=uncertain,
            cortex_read=lambda k: None, cortex_write=lambda k, v: None,
            allow_notion_write=True, allow_cortex_write=True)
        self.assertEqual(r.next_action, "NOTION_WRITE_OUTCOME_UNCERTAIN_RECONCILE")
        self.assertFalse(c)

    def test_mismatched_identity_fails(self):
        with self.assertRaises(ValueError):
            run_handoff(transcript="x", notion_page_id="n", cortex_module_name="c",
                analysis="a", notion_read=lambda k: Observed("wrong", "x"),
                notion_write=lambda k, v: None, cortex_read=lambda k: None,
                cortex_write=lambda k, v: None)


if __name__ == "__main__":
    unittest.main()

# Include composed event-to-handoff tests in the existing bounded CI suite.
from test_transcript_event_execution import EventExecutionTests  # noqa: E402,F401

# Exercise runner evidence contract in existing provider handoff CI.
from test_transcript_runner_evidence import RunnerEvidenceTests  # noqa: E402,F401

# Exercise source-bound Gemini review evidence in existing handoff CI.
from test_transcript_gemini_review import GeminiReviewBindingTests  # noqa: E402,F401

# Exercise reviewed transcript composition in existing handoff CI.
from test_transcript_reviewed_execution import ReviewedExecutionTests  # noqa: E402,F401

# Exercise bounded Gemini invocation adapter in existing handoff CI.
from test_transcript_gemini_runtime import GeminiRuntimeTests  # noqa: E402,F401
