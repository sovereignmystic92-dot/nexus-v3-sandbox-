"""Offline-only tests; no credentials, HTTP, Notion, GitHub, or side effects."""
import hashlib
import unittest
from nexus_sandbox.checkpoint_json import encode
from nexus_sandbox.processing_pipeline import Receipt, STAGES
from nexus_sandbox.resume_decision import decide_resume

BINDING = dict(run_id='sandbox-recovery-001', source_id='synthetic:test',
               source_sha256=hashlib.sha256(b'fixture').hexdigest(),
               destination_id='synthetic-destination', policy_revision='v3-test',
               code_revision='offline', schema_version=1)


def snapshot(count=0, pending=None, binding=None):
    b = binding or BINDING
    receipts = tuple(Receipt(b['run_id'], stage, True, ('synthetic:evidence:'+str(i),))
                     for i, stage in enumerate(STAGES[:count]))
    return encode(dict(binding=b, receipts=receipts, pending=pending), b)


class ResumeDecisionTests(unittest.TestCase):
    def decide(self, data, **flags):
        return decide_resume(data, BINDING, inventory_complete=True,
                             authority_verified=True, **flags)

    def test_fresh_enrolled_job_requires_intent_before_first_stage(self):
        d = self.decide(snapshot())
        self.assertEqual((d.status, d.pending, d.next_action),
                         ('READY_FOR_GATED_EXECUTOR', STAGES[0], 'VERIFY_PREREQUISITES_AND_SAVE_INTENT'))

    def test_completed_receipts_are_not_replayed(self):
        d = self.decide(snapshot(3))
        self.assertEqual(d.completed, STAGES[:3])
        self.assertEqual(d.pending, STAGES[3])

    def test_pending_intent_is_reconciliation_only(self):
        d = self.decide(snapshot(2, STAGES[2]))
        self.assertEqual(d.status, 'RECONCILE_ONLY')
        self.assertEqual(d.next_action, 'OBSERVE_DESTINATION_AND_RECONCILE')

    def test_last_stage_pending_is_still_uncertain(self):
        self.assertEqual(self.decide(snapshot(6, STAGES[6])).status, 'RECONCILE_ONLY')

    def test_all_receipts_no_action(self):
        d = self.decide(snapshot(7))
        self.assertEqual((d.status, d.next_action), ('COMPLETE', 'NO_ACTION'))

    def test_truncated_inventory_blocks(self):
        d = decide_resume(snapshot(), BINDING, inventory_complete=False,
                          authority_verified=True)
        self.assertEqual(d.next_action, 'OBTAIN_COMPLETE_INVENTORY')

    def test_missing_authority_blocks(self):
        d = decide_resume(snapshot(), BINDING, inventory_complete=True,
                          authority_verified=False)
        self.assertEqual(d.next_action, 'VERIFY_CURRENT_AUTHORITY')

    def test_missing_checkpoint_is_not_initialized(self):
        self.assertEqual(self.decide(None).next_action, 'INVESTIGATE_CHECKPOINT')

    def test_wrong_job_binding_blocks(self):
        different = dict(BINDING, run_id='other-job')
        self.assertEqual(self.decide(snapshot(binding=different)).status, 'BLOCKED')

    def test_duplicate_json_key_blocks(self):
        wire = snapshot().replace('"pending":null', '"pending":null,"pending":null')
        self.assertEqual(self.decide(wire).status, 'BLOCKED')

    def test_boolean_flags_must_be_actual_bools(self):
        with self.assertRaises(ValueError):
            decide_resume(snapshot(), BINDING, inventory_complete=1, authority_verified=True)


if __name__ == '__main__':
    unittest.main()
