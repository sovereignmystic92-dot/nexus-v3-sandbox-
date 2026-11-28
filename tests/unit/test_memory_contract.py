"""Offline checks for the provider-neutral Skill Forge memory contract."""

from copy import deepcopy
from hashlib import sha256
import json
import unittest

from nexus_sandbox.checkpoint_ledger import manifest_hash
from nexus_sandbox.memory_contract import SCHEMA, encode_revision, source_reference, validate_resume


OBSERVED = "2026-11-15T12:00:00Z"
RECEIPT = b'{"verdict": "verified"}\n'


def checkpoint(sequence, previous=None, receipt_id="evidence"):
    body = {
        "mission_id": "mission", "sequence": sequence,
        "observed_at_utc": OBSERVED, "previous_checkpoint_sha256": previous,
        "verified_receipt": {
            "store_scope": "offline", "receipt_id": receipt_id,
            "receipt_sha256": sha256(RECEIPT).hexdigest(),
        },
    }
    return dict(body, checkpoint_sha256=manifest_hash(body))


class MemoryContractTests(unittest.TestCase):
    def setUp(self):
        self.source = source_reference("synthetic", "offline", "source", "1", "é\r\n")
        self.record = {
            "schema_version": SCHEMA, "store_scope": "offline", "module_id": "target",
            "name": "derived", "version": 1, "content": "é\r\n",
            "content_sha256": sha256("é\r\n".encode()).hexdigest(),
            "dependencies": ["source", "earlier"], "source": self.source,
            "observed_at_utc": OBSERVED,
            "verification": {
                "status": "verified", "evidence_class": "offline_synthetic",
                "observed_at_utc": OBSERVED, "receipt_ref": "evidence",
            },
        }

    def test_revision_round_trip_preserves_bytes_and_edge_order(self):
        self.assertEqual(json.loads(encode_revision(self.record, fresh_source=self.source)), self.record)
        with self.assertRaisesRegex(ValueError, "content digest"):
            encode_revision(dict(self.record, content="é\n"), fresh_source=self.source)

    def test_verified_revision_requires_matching_fresh_source(self):
        for source in (None, dict(self.source, revision_id="2"), dict(self.source, store_scope="other")):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "fresh source"):
                encode_revision(self.record, fresh_source=source)
        held = deepcopy(self.record)
        held["source"] = None
        held["verification"].update(status="held", receipt_ref=None)
        self.assertEqual(json.loads(encode_revision(held)), held)

    def resume(self, prefix, candidate, *, receipt=RECEIPT, genesis=False):
        def resolve(mission_id, scope, receipt_id):
            self.assertEqual((mission_id, scope, receipt_id), ("mission", "offline", "evidence"))
            return receipt
        return validate_resume(prefix, candidate, mission_id="mission",
                               resolve_verified_receipt=resolve, authorize_genesis=genesis)

    def test_append_and_explicit_genesis(self):
        first = checkpoint(1)
        second = checkpoint(2, first["checkpoint_sha256"])
        self.assertEqual(self.resume([first], [first, second]), second["checkpoint_sha256"])
        self.assertEqual(self.resume([], [first], genesis=True), first["checkpoint_sha256"])
        with self.assertRaisesRegex(ValueError, "Genesis"):
            self.resume([], [first])
        with self.assertRaisesRegex(ValueError, "unavailable"):
            self.resume(None, [first], genesis=True)

    def test_rejects_rehashed_rewrite_truncation_and_changed_receipt(self):
        first = checkpoint(1)
        with self.assertRaisesRegex(ValueError, "rewritten"):
            self.resume([first], [checkpoint(1, receipt_id="other")])
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.resume([first], [])
        with self.assertRaisesRegex(ValueError, "receipt bytes"):
            self.resume([first], [first], receipt=RECEIPT.rstrip())
        with self.assertRaisesRegex(ValueError, "hash chain"):
            self.resume([first], [first, checkpoint(2)])
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.resume([], [dict(first, checkpoint_sha256="0" * 64)], genesis=True)
