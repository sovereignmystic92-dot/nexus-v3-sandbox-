"""Synthetic tests for transcript-only five-pass review eligibility."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.event_router import Enrollment, Event, ObserverQueue
from nexus_sandbox.transcript_promotion import FivePassLedger

REV = hashlib.sha256(b'transcript').hexdigest()
POLICY = 'policy-v1'
CODE = 'code-v1'
AUTH = 'authorized-fixture'


class FivePassTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.queue = ObserverQueue(root/'queue.sqlite', initialize=True)
        self.ledger = FivePassLedger(root/'promotion.sqlite', initialize=True)

    def submit(self, i, result='VERIFIED_SUCCESS', *, code=CODE, readback=True):
        source = 'transcript:'+str(i)
        enrolled = Enrollment(source, POLICY, code, AUTH,
                              ('INSPECT_TRANSCRIPT',), 100)
        routed = self.queue.route(Event('evt:'+str(i), 'SOURCE_READY', source,
                                        REV,'SOURCE'), enrolled)
        self.assertEqual(routed.status,'PLANNED')
        evidence = dict(job_id=routed.job_id,source_id=source,revision_sha256=REV,
                        policy_revision=POLICY,code_revision=code,authorization_ref=AUTH,
                        result=result,evidence_id='proof:'+str(i),
                        verified_readback=readback)
        return evidence

    def record(self, evidence):
        return self.ledger.record(evidence, observer_queue=self.queue)

    def test_five_distinct_passes_trigger_review_only(self):
        for i in range(1,5):
            d = self.record(self.submit(i))
            self.assertEqual((d.status,d.consecutive),('OBSERVING',i))
        d = self.record(self.submit(5))
        self.assertEqual((d.status,d.consecutive),
                         ('REVIEW_ELIGIBLE',5))
        self.assertEqual(d.next_action,'REQUEST_INDEPENDENT_PROMOTION_REVIEW')

    def test_duplicate_event_does_not_increment(self):
        proof=self.submit(1)
        self.assertEqual(self.record(proof).consecutive,1)
        self.assertEqual(self.record(proof).status,'DUPLICATE')
        self.assertEqual(self.record(self.submit(2)).consecutive,2)

    def test_failed_job_resets_streak(self):
        self.record(self.submit(1))
        self.record(self.submit(2))
        self.assertEqual(self.record(self.submit(3,'FAILED')).status,'STREAK_RESET')
        self.assertEqual(self.record(self.submit(4)).consecutive,1)

    def test_uncertain_does_not_promote(self):
        self.record(self.submit(1))
        self.assertEqual(self.record(self.submit(2,'INTERRUPTED')).status,'HELD_UNCERTAIN')
        self.assertEqual(self.record(self.submit(3)).consecutive,1)

    def test_inconclusive_breaks_success_run(self):
        self.record(self.submit(1))
        self.record(self.submit(2,'INCONCLUSIVE'))
        self.assertEqual(self.record(self.submit(3)).consecutive,1)

    def test_changed_configuration_requires_new_streak(self):
        self.record(self.submit(1))
        self.assertEqual(self.record(self.submit(2,code='code-v2')).consecutive,1)

    def test_absent_readback_blocks_success(self):
        proof=self.submit(1,readback=False)
        self.assertEqual(self.record(proof).next_action,'VERIFY_COMPLETION_READBACK')
        self.assertEqual(self.record(self.submit(2)).consecutive,1)

    def test_unplanned_job_blocks(self):
        proof=self.submit(1)
        proof['job_id']='f'*64
        self.assertEqual(self.record(proof).status,'BLOCKED')

    def test_wrong_source_binding_blocks(self):
        proof=self.submit(1)
        proof['source_id']='different'
        self.assertEqual(self.record(proof).next_action,'RECONCILE_JOB_BINDING')

    def test_conflicting_second_result_blocks(self):
        proof=self.submit(1)
        self.record(proof)
        changed=dict(proof,evidence_id='alternate-proof')
        self.assertEqual(self.record(changed).next_action,'RECONCILE_CONFLICTING_EVIDENCE')

    def test_missing_ledger_not_reset(self):
        with self.assertRaises(ValueError):
            FivePassLedger(Path(self.temp.name)/'absent.sqlite')


if __name__ == '__main__':
    unittest.main()
