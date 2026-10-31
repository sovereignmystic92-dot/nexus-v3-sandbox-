import tempfile
from pathlib import Path
import unittest
from nexus_sandbox.provider_custody import CustodyLedger, digest


class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"ledger.sqlite"
        self.ledger=CustodyLedger(self.path,initialize=True)
        self.intent=dict(transaction_id="nxs:pilot:one",
            notion_source_id="notion:transcript:one",
            notion_revision="r1",notion_sha256="a"*64,
            cortex_output_id="cortex:output:one",
            cortex_revision="v1",cortex_sha256="b"*64,
            policy_revision="p1")
        self.proof=dict(transaction_id=self.intent["transaction_id"],
            intent_sha256=digest(self.intent),
            notion_source_id=self.intent["notion_source_id"],
            notion_revision=self.intent["notion_revision"],
            notion_sha256=self.intent["notion_sha256"],
            cortex_output_id=self.intent["cortex_output_id"],
            cortex_revision=self.intent["cortex_revision"],
            cortex_sha256=self.intent["cortex_sha256"],
            notion_complete=True,cortex_complete=True,
            authority_verified=True,independent_readback=True)

    def test_prepare_does_not_write(self):
        x=self.ledger.prepare(self.intent)
        self.assertEqual(x.status,"PREPARED")
        self.assertEqual(x.provider_writes,0)
        self.assertFalse(x.automatic_execution)
        self.assertEqual(x.cp09,"NOT_PROVEN")

    def test_duplicate_prepare_no_replay(self):
        self.ledger.prepare(self.intent)
        self.assertEqual(self.ledger.prepare(self.intent).next_action,
                         "NO_REPLAY_OR_DUPLICATE_WRITE")

    def test_conflicting_transaction_rejected(self):
        self.ledger.prepare(self.intent)
        self.assertEqual(self.ledger.prepare(dict(self.intent,cortex_revision="v2")).status,"HELD")

    def test_dispatched_state_persists_across_restart(self):
        self.ledger.prepare(self.intent)
        self.assertEqual(self.ledger.mark_dispatching(self.intent["transaction_id"]).status,"DISPATCHING")
        second=CustodyLedger(self.path)
        self.assertEqual(second.prepare(self.intent).status,"DISPATCHING")

    def test_cannot_dispatch_twice(self):
        self.ledger.prepare(self.intent)
        self.ledger.mark_dispatching(self.intent["transaction_id"])
        self.assertEqual(self.ledger.mark_dispatching(self.intent["transaction_id"]).status,"HELD")

    def test_proof_only_after_dispatch(self):
        self.ledger.prepare(self.intent)
        self.assertEqual(self.ledger.reconcile(self.proof).status,"HELD")

    def test_matching_proof_only_attests_supplied_evidence(self):
        self.ledger.prepare(self.intent)
        self.ledger.mark_dispatching(self.intent["transaction_id"])
        x=self.ledger.reconcile(self.proof)
        self.assertEqual(x.status,"READBACK_MATCHED")
        self.assertEqual(x.provider_writes,0)

    def test_mismatch_does_not_replay(self):
        self.ledger.prepare(self.intent)
        self.ledger.mark_dispatching(self.intent["transaction_id"])
        self.assertEqual(self.ledger.reconcile(dict(self.proof,cortex_sha256="c"*64)).next_action,
                         "RECONCILE_MISMATCH_NO_RETRY")

    def test_incomplete_readback_blocks(self):
        self.ledger.prepare(self.intent)
        self.ledger.mark_dispatching(self.intent["transaction_id"])
        self.assertEqual(self.ledger.reconcile(dict(self.proof,cortex_complete=False)).status,"HELD")

    def test_string_authority_not_accepted(self):
        self.ledger.prepare(self.intent)
        self.ledger.mark_dispatching(self.intent["transaction_id"])
        self.assertEqual(self.ledger.reconcile(dict(self.proof,authority_verified="true")).status,"HELD")

    def test_unknown_receipt_field_rejected(self):
        self.ledger.prepare(self.intent)
        self.ledger.mark_dispatching(self.intent["transaction_id"])
        self.assertEqual(self.ledger.reconcile(dict(self.proof,secret="not allowed")).status,"HELD")

    def test_missing_ledger_is_never_recreated(self):
        with self.assertRaises(ValueError):
            CustodyLedger(Path(self.tmp.name)/"missing.sqlite")

    def test_invalid_digest_rejected(self):
        self.assertEqual(self.ledger.prepare(dict(self.intent,notion_sha256="x")).status,"HELD")

    def test_missing_dispatch_unknown_transaction(self):
        self.assertEqual(self.ledger.mark_dispatching("unknown").status,"HELD")

    def test_symlink_ledger_rejected(self):
        link=Path(self.tmp.name)/"pointer"
        link.symlink_to(self.path)
        with self.assertRaises(ValueError):
            CustodyLedger(link)
