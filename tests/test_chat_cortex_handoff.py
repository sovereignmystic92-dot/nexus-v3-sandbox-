import unittest
from nexus_sandbox.chat_cortex_handoff import make_packet, validate_receipt

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

class HandoffTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(make_packet(FIELDS), make_packet(dict(reversed(list(FIELDS.items())))))
    def test_wrong_actor(self):
        with self.assertRaises(ValueError):
            make_packet({**FIELDS, "actor": "github-runner"})
    def test_bad_digest(self):
        with self.assertRaises(ValueError):
            make_packet({**FIELDS, "source_sha256": "not-a-digest"})
    def test_unknown_secret_key(self):
        with self.assertRaises(ValueError):
            make_packet({**FIELDS, "client_secret": "not allowed"})
    def test_receipt_verified(self):
        packet = make_packet(FIELDS)
        self.assertTrue(validate_receipt(packet, {
            "packet_id": packet["packet_id"], "actor": "chatgpt-connected-cortex",
            "status": "READBACK_VERIFIED", "readback_matched": True,
            "audit_gate_promoted": False}))
    def test_receipt_unverified_rejected(self):
        packet = make_packet(FIELDS)
        with self.assertRaises(ValueError):
            validate_receipt(packet, {
                "packet_id": packet["packet_id"], "actor": "chatgpt-connected-cortex",
                "status": "READBACK_VERIFIED", "readback_matched": False,
                "audit_gate_promoted": False})

if __name__ == "__main__":
    unittest.main()
