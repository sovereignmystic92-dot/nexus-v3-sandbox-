"""Offline negative tests for CP05 read-only probe; not live provider evidence."""
import unittest
from nexus_sandbox.cp05_readonly_probe import probe, SOURCE_ID, MODULE_ID, SOURCE_URL, VIDEO_URL


class Fake:
    def __init__(self):
        self.calls = []
        self.source = {"id": SOURCE_ID, "video_id": "kokDVXUGdes", "verbatim": False}
        self.module = {"id": MODULE_ID, "version": 1, "content": SOURCE_URL + "\n" + VIDEO_URL}
    def read_notion_page(self, key):
        self.calls.append(("notion", key))
        return self.source
    def read_cortex_module(self, key):
        self.calls.append(("cortex", key))
        return self.module


class ProbeTests(unittest.TestCase):
    def run_probe(self, t, **kwargs):
        args = {"principal_ref": "test-host", "host_auth_verified": True,
                "independent_receipt_readback": True}
        args.update(kwargs)
        return probe(t, **args)

    def test_exact_ids_not_uniqueness(self):
        t = Fake()
        r = self.run_probe(t)
        self.assertEqual(r.status, "MATCHED_EXACT_IDS_UNIQUENESS_UNVERIFIED")
        self.assertEqual((r.reads, r.writes, r.completion_verified), (2, 0, False))
        self.assertEqual(t.calls, [("notion", SOURCE_ID), ("cortex", MODULE_ID)])

    def test_auth_denial_makes_no_calls(self):
        t = Fake()
        r = self.run_probe(t, host_auth_verified=False)
        self.assertEqual((r.status, r.reads, t.calls), ("BLOCKED_HOST_AUTH", 0, []))

    def test_readback_missing_makes_no_calls(self):
        t = Fake()
        self.assertEqual(self.run_probe(t, independent_receipt_readback=False).status,
                         "BLOCKED_RECEIPT_READBACK")
        self.assertFalse(t.calls)

    def test_source_mismatch_blocks_cortex_read(self):
        t = Fake(); t.source["id"] = "wrong"
        self.assertEqual(self.run_probe(t).status, "BLOCKED_SOURCE_IDENTITY")
        self.assertEqual(len(t.calls), 1)

    def test_fidelity_must_be_explicitly_non_verbatim(self):
        t = Fake(); t.source["verbatim"] = True
        self.assertEqual(self.run_probe(t).status, "BLOCKED_FIDELITY_UNVERIFIED")

    def test_revision_drift(self):
        t = Fake(); t.module["version"] = 2
        self.assertEqual(self.run_probe(t).status, "BLOCKED_MODULE_REVISION")

    def test_missing_provenance(self):
        t = Fake(); t.module["content"] = VIDEO_URL
        self.assertEqual(self.run_probe(t).status, "BLOCKED_PROVENANCE")

    def test_cortex_outage(self):
        t = Fake()
        def fail(_): raise TimeoutError("unavailable")
        t.read_cortex_module = fail
        self.assertEqual(self.run_probe(t).status, "BLOCKED_CORTEX_UNAVAILABLE")

    def test_no_write_api_exposed(self):
        t = Fake()
        self.assertFalse(hasattr(t, "create") or hasattr(t, "update"))
        self.assertEqual(self.run_probe(t).writes, 0)


if __name__ == "__main__":
    unittest.main()
