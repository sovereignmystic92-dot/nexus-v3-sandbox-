"""Verify recorded Notion tool observations offline; never writes to Notion.

The operator fetches the root and every direct child and supplies structured
fetch objects. This proves adapter behavior on those observations, not a live
network transport or completeness of a service-level listing API.
"""

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexus_sandbox.notion_adapter import Binding, Listing, NotionAdapter, Page


def compact(value):
    return value.replace("-", "")


def usable(document):
    return (document.get("metadata", {}).get("type") == "page"
            and not document.get("truncated") and not document.get("unknown_block_count")
            and "<unknown " not in document.get("text", ""))


class RecordedTransport:
    def __init__(self, observation):
        self.root = observation["root"]
        self.children = observation["children"]
        self.create_calls = 0

    def sandbox_marker(self, parent_id):
        root = self.root
        if (not usable(root) or compact(root["id"]) != compact(parent_id)
                or not any(marker in root["text"] for marker in (
                    "`synthetic:notion:sandbox:v1`", "<code>synthetic:notion:sandbox:v1</code>"))):
            return "unconfirmed"
        return "synthetic:notion:sandbox:v1"

    @staticmethod
    def page(document):
        text = document["text"]
        matches = re.findall(r"```json\n([\s\S]*?)\n```", text)
        parents = re.findall(r'<parent-page url="https://app.notion.com/p/([0-9a-f-]+)"', text)
        if not usable(document) or len(matches) != 1 or len(parents) != 1:
            raise ValueError("Incomplete or ambiguous direct-child observation")
        record = json.loads(matches[0])
        if record.get("adapter_schema") != 1 or record.get("title") != document["title"]:
            raise ValueError("Unrecognized adapter record or title mismatch")
        if type(record.get("synthetic")) is not bool:
            raise ValueError("Synthetic flag must be boolean")
        return Page(document["id"], parents[0], record["key"], document["title"],
                    record["payload"], record["payload_sha256"], record["synthetic"])

    def find_direct_children(self, parent_id, key):
        content = self.root["text"].split("<content>", 1)[1].split("</content>", 1)[0]
        ids = re.findall(r'<page url="https://app.notion.com/p/([0-9a-f-]+)"', content)
        observed = [compact(child["id"]) for child in self.children]
        complete = (len(observed) == len(set(observed)) == len(ids)
                    and set(observed) == {compact(page_id) for page_id in ids}
                    and all(usable(child) for child in self.children))
        matches = []
        for child in self.children:
            if key in child["text"]:
                try:
                    matches.append(self.page(child))
                except (ValueError, KeyError):
                    complete = False
        # Notion fetch returns compact parent URLs; bind to the same canonical
        # compact UUID representation supplied to this observation-only bridge.
        return Listing(tuple(matches), complete)

    def fetch_page(self, page_id):
        matches = [d for d in self.children if compact(d["id"]) == compact(page_id)]
        if len(matches) != 1:
            raise ValueError("Known page observation absent or ambiguous")
        return self.page(matches[0])

    def create_child(self, binding):
        self.create_calls += 1
        raise RuntimeError("Read-only recorded transport cannot create pages")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.observations.read_text())
    parent = compact(data["root"]["id"])
    transport = RecordedTransport(data)
    binding = Binding(parent_id=parent, **data["binding"])
    receipt = NotionAdapter(args.journal, parent, transport).ensure(binding)
    print(json.dumps({"status": receipt.status, "page_id": receipt.page_id,
                      "reason": receipt.reason, "create_calls": transport.create_calls,
                      "scope": "offline adapter evaluation of recorded live tool reads; not an SDK transport"}))
    return 0 if receipt.status == "VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
