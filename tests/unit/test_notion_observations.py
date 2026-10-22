"""Reject incomplete recorded tool reads before claiming reconciliation."""

from dataclasses import asdict
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from notion_observations import RecordedTransport
from nexus_sandbox.notion_adapter import Binding

ROOT = "00000000000000000000000000000001"
PAGE = "00000000000000000000000000000002"


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.binding = Binding("synthetic:request:recorded", ROOT, "Synthetic observation", "Fictional payload")
        record = {k: v for k, v in asdict(self.binding).items() if k != "parent_id"}
        record.update(adapter_schema=1, synthetic=True, payload_sha256=self.binding.payload_sha256)
        self.child = {"id": PAGE, "title": self.binding.title, "metadata": {"type": "page"},
                      "text": '<parent-page url="https://app.notion.com/p/' + ROOT + '"/>\n```json\n'
                              + json.dumps(record) + '\n```'}
        self.root = {"id": ROOT, "metadata": {"type": "page"}, "text": '<content>\n`synthetic:notion:sandbox:v1`\n<page url="https://app.notion.com/p/' + PAGE + '">Child</page>\n</content>'}

    def transport(self, children=None):
        return RecordedTransport({"root": self.root, "children": [self.child] if children is None else children})

    def test_complete_direct_child_record_is_readable(self):
        listing = self.transport().find_direct_children(ROOT, self.binding.key)
        self.assertTrue(listing.complete)
        self.assertEqual(len(listing.pages), 1)
        self.assertEqual(listing.pages[0].payload_sha256, self.binding.payload_sha256)

    def test_both_observed_inline_code_marker_encodings_are_accepted(self):
        for marker in ("`synthetic:notion:sandbox:v1`", "<code>synthetic:notion:sandbox:v1</code>"):
            self.root["text"] = self.root["text"].replace("`synthetic:notion:sandbox:v1`", marker)
            self.assertEqual(self.transport().sandbox_marker(ROOT), "synthetic:notion:sandbox:v1")

    def test_missing_child_or_duplicate_fetch_is_incomplete(self):
        for children in ([], [self.child, self.child]):
            self.assertFalse(self.transport(children).find_direct_children(ROOT, self.binding.key).complete)

    def test_unknown_or_truncated_blocks_fail_closed(self):
        self.child["truncated"] = True
        self.assertFalse(self.transport().find_direct_children(ROOT, self.binding.key).complete)

    def test_unrecognized_adapter_or_title_mismatch_is_incomplete(self):
        self.child["title"] = "Different actual title"
        self.assertFalse(self.transport().find_direct_children(ROOT, self.binding.key).complete)
