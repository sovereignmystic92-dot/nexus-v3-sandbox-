"""Adversarial offline CP05 receipt bridge checks."""
import copy
import hashlib
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from cp05_receipt_bridge import bridge, validate_source
from cp05_supervised_receipt_verify import PAGE, MODULE, PAYLOAD

REV = "2026-11-05T20:00:00.000Z"
RUN = 123456

def pair():
    source = {"schema": "NEXUS_CP05_NOTION_SOURCE_SNAPSHOT_V1",
              "mode": "READ_ONLY", "notion_page_id": PAGE,
              "github_job_name": "notion-fixture", "github_run_id": RUN,
              "provider_writes": 0, "checkpoint": "NOT_ATTESTED",
              "cortex_host_auth": "NOT_ATTESTED", "block_count": 1,
              "canonical_inventory_sha256": "a" * 64,
              "fixture_payload_sha256": "b" * 64,
              "source_revision": REV}
    supervised = {"schema": "NEXUS_CP05_SUPERVISED_READ_V1",
                  "mode": "READ_ONLY", "attestation": "NOT_ATTESTED",
                  "notion_page_id": PAGE, "cortex_module_id": MODULE,
                  "fixture_payload_sha256": hashlib.sha256(PAYLOAD.encode()).hexdigest(),
                  "provider_writes": 0, "github_run_id": RUN,
                  "github_job_id": 123457, "source_last_edited_at": REV}
    return source, supervised

class BridgeTests(unittest.TestCase):
    def test_matches_without_promoting(self):
        s, t = pair()
        result = bridge(s, t)
        self.assertEqual(result["checkpoint"], "NOT_ATTESTED")
        self.assertEqual(result["host_provenance"], "NOT_VERIFIED")

    def test_source_rejections(self):
        for key, bad in [("schema", "wrong"), ("mode", "WRITE"),
                         ("notion_page_id", "wrong"), ("github_job_name", "wrong"),
                         ("github_run_id", True), ("provider_writes", False),
                         ("provider_writes", 1), ("checkpoint", "SOURCE_MATCHED"),
                         ("cortex_host_auth", "VERIFIED"), ("block_count", 0),
                         ("canonical_inventory_sha256", "xyz"),
                         ("fixture_payload_sha256", "A" * 64),
                         ("source_revision", "invalid")]:
            with self.subTest(key=key, bad=bad):
                s, _ = pair()
                s[key] = bad
                with self.assertRaises(ValueError):
                    validate_source(s)

    def test_cross_receipt_rejections(self):
        for key, bad in [("github_run_id", RUN + 1),
                         ("source_last_edited_at", "2026-11-04T20:00:00Z"),
                         ("attestation", "SOURCE_MATCHED"),
                         ("notion_page_id", "wrong")]:
            with self.subTest(key=key):
                s, t = pair()
                t[key] = bad
                with self.assertRaises(ValueError):
                    bridge(s, t)

if __name__ == "__main__":
    unittest.main()
