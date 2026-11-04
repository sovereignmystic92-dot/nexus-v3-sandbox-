"""Synthetic regression tests for Notion snapshot guard; no provider calls."""
import unittest

from nexus_sandbox.notion_snapshot_guard import snapshot, compare_snapshots, NotionSnapshot

TIME = "2026-11-04T15:38:03.604Z"


class NotionSnapshotGuardTests(unittest.TestCase):
    def setUp(self):
        self.a = snapshot("page1", TIME, "complete content")

    def test_identical_authenticated_complete(self):
        self.assertEqual(compare_snapshots(self.a, snapshot("page1", TIME, "complete content"),
                         authenticated=True, complete_inventory=True), "MATCHED")

    def test_missing_host_attestation_fails_closed(self):
        self.assertNotEqual(compare_snapshots(self.a, self.a), "MATCHED")
        self.assertNotEqual(compare_snapshots(self.a, self.a, authenticated=True), "MATCHED")
        self.assertNotEqual(compare_snapshots(self.a, self.a, authenticated=1,
                            complete_inventory=True), "MATCHED")

    def test_stale_revision_and_changed_content_rejected(self):
        cases = [
            (snapshot("other", TIME, "complete content"), "BLOCKED_PAGE_MISMATCH"),
            (snapshot("page1", "2026-11-04T15:39:03.604Z", "complete content"),
             "BLOCKED_CHANGED_TIMESTAMP"),
            (snapshot("page1", TIME, "modified content"), "BLOCKED_CHANGED_CONTENT"),
        ]
        for observed, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(compare_snapshots(self.a, observed,
                                 authenticated=True, complete_inventory=True), expected)

    def test_bad_inputs_rejected(self):
        for args in [("", TIME, "text"), ("page1", "fixture-r1", "text"),
                     ("page1", TIME, "")]:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    snapshot(*args)
        malformed = NotionSnapshot("page1", TIME, "not-a-sha")
        self.assertEqual(compare_snapshots(self.a, malformed, authenticated=True,
                         complete_inventory=True), "BLOCKED_INVALID_SNAPSHOT")


if __name__ == "__main__":
    unittest.main()
