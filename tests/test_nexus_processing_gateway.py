import unittest
from nexus_sandbox.nexus_processing_gateway import process
from nexus_sandbox.transcript_live_handoff import Observed


class GatewayTests(unittest.TestCase):
    def invoke(self, mode, grants):
        notion, cortex = {}, {}
        result = process(
            mode=mode, source_url="https://youtu.be/_p6lrFsVPzQ",
            transcript="Full source.", notion_page_id="notion-1",
            cortex_module_name="module-1", analysis="Analysis.",
            grants=grants,
            notion_read=lambda k: Observed(k, notion[k]) if k in notion else None,
            notion_write=lambda k, v: notion.__setitem__(k, v),
            cortex_read=lambda k: Observed(k, cortex[k]) if k in cortex else None,
            cortex_write=lambda k, v: cortex.__setitem__(k, v))
        return result, notion, cortex

    def test_all_modes_same_completion(self):
        grants = dict(process=True, notion_write=True, cortex_write=True)
        for mode in ("manual", "gemini", "scheduled"):
            with self.subTest(mode=mode):
                result, notion, cortex = self.invoke(mode, grants)
                self.assertEqual(result.status, "READBACK_MATCHED")
                self.assertEqual(notion["notion-1"], "Full source.")
                self.assertIn(result.source_sha256, cortex["module-1"])

    def test_all_modes_deny_without_grant(self):
        grants = dict(process=False, notion_write=True, cortex_write=True)
        for mode in ("manual", "gemini", "scheduled"):
            result, notion, cortex = self.invoke(mode, grants)
            self.assertEqual(result.next_action, "AUTHORIZE_NEXUS_PROCESSING")
            self.assertEqual((notion, cortex), ({}, {}))

    def test_no_write_grants(self):
        result, notion, cortex = self.invoke(
            "gemini", dict(process=True, notion_write=False, cortex_write=False))
        self.assertEqual(result.status, "BLOCKED")
        self.assertFalse(notion)
        self.assertFalse(cortex)

    def test_unknown_mode_fails(self):
        with self.assertRaises(ValueError):
            self.invoke("other", dict(process=True, notion_write=True, cortex_write=True))

    def test_missing_grant_fails(self):
        with self.assertRaises(ValueError):
            self.invoke("manual", dict(process=True, notion_write=True))


if __name__ == "__main__":
    unittest.main()
