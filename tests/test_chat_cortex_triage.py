import json
import unittest
from nexus_sandbox.chat_cortex_handoff import make_packet
from nexus_sandbox.chat_cortex_triage import triage_packet, triage_batch

FIELDS = {
    "source_issue_url": "https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/263",
    "source_sha256": "a" * 64,
    "source_revision": "2026-11-08",
    "destination_module": "Nexus CP05 — Chat–Cortex Bridge Pilot 2026-11-08",
    "intent": "Reconcile bounded operational evidence",
    "evidence_class": "operational-decision",
    "actor": "chatgpt-connected-cortex",
    "scope": "single-module-write",
    "approval_reference": "owner direction 2026-11-08",
}
class TriageTests(unittest.TestCase):
    def setUp(self):
        self.packet = make_packet(FIELDS)
    def test_valid_requires_review(self):
        self.assertEqual(triage_packet(json.dumps(self.packet))["decision"], "REVIEW_REQUIRED")
    def test_tamper_blocked(self):
        self.packet["request"]["intent"] = "changed"
        self.assertEqual(triage_packet(self.packet)["decision"], "BLOCKED_INVALID_PACKET")
    def test_false_auth_claim_blocked(self):
        self.packet["provider_authenticated_by_github"] = True
        self.assertEqual(triage_packet(self.packet)["decision"], "BLOCKED_INVALID_PACKET")
    def test_unverified_write_claim_blocked(self):
        self.packet["cortex_write_verified"] = True
        self.assertEqual(triage_packet(self.packet)["decision"], "BLOCKED_INVALID_PACKET")
    def test_dedup(self):
        self.assertEqual(triage_batch([self.packet, self.packet])[1]["decision"], "DUPLICATE")
    def test_limit(self):
        with self.assertRaises(ValueError):
            triage_batch([self.packet] * 21)
    def test_malformed(self):
        self.assertEqual(triage_packet("{")["decision"], "BLOCKED_INVALID_PACKET")

if __name__ == "__main__":
    unittest.main()
