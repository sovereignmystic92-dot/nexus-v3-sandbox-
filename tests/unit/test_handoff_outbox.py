from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from nexus_sandbox.handoff_outbox import Handoff, HandoffHold, HandoffOutbox


NOW = '2026-11-12T15:30:00+00:00'


class HandoffOutboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'handoffs.sqlite'
        self.box = HandoffOutbox.initialize(self.path, 'synthetic:worker:one')
        self.value = Handoff(
            finding_id='NXS-FINDING-ONE', source_ref='notion:source:one',
            source_revision='sha256:' + 'a' * 64,
            destination='task:nexus-transcript-backlog',
            next_action='Map the exact source to its Cortex output and read it back.',
            completion_criteria=('Exact source mapping saved',
                                 'Cortex output independently read back'),
            authorization_ref='owner-storage-decision-20261112', priority=10)
        self.recorded = self.box.record(self.value, event_id='record:one',
            actor='maintenance', observed_at_utc=NOW)

    def move(self, state, n, **kw):
        return self.box.transition(self.recorded['handoff_id'],
            event_id=f'event:{n}', to_state=state, actor='synthetic:consumer',
            observed_at_utc=NOW, **kw)

    def test_full_receipt_chain_requires_independent_completion_readback(self):
        self.move('ROUTING', 1)
        self.move('ROUTED', 2, evidence_ref='github:delivery:1')
        self.move('ACCEPTED', 3, evidence_ref='task:acceptance:1')
        self.move('IN_PROGRESS', 4, evidence_ref='task:checkpoint:1')
        with self.assertRaises(ValueError):
            self.move('VERIFIED_COMPLETE', 5, evidence_ref='cortex:module:1')
        result = self.move('VERIFIED_COMPLETE', 6,
            evidence_ref='cortex:module:1', readback_ref='cortex:readback:1')
        self.assertEqual(result['state'], 'VERIFIED_COMPLETE')
        self.assertEqual([event['to_state'] for event in result['events']],
            ['RECORDED', 'ROUTING', 'ROUTED', 'ACCEPTED', 'IN_PROGRESS',
             'VERIFIED_COMPLETE'])

    def test_deliver_one_pushes_recorded_item_to_routed(self):
        seen = []
        result = self.box.deliver_one(actor='synthetic:dispatcher',
            intent_event_id='route:intent:1', routed_event_id='route:saved:1',
            observed_at_utc=NOW,
            deliver=lambda binding: (seen.append(binding) or
                                      {'delivery_ref': 'github:issue:202#handoff'}))
        self.assertEqual(result['state'], 'ROUTED')
        self.assertEqual(seen[0]['finding_id'], self.value.finding_id)

    def test_uncertain_delivery_is_not_replayed(self):
        calls = []
        def fail(binding):
            calls.append(binding)
            raise TimeoutError('synthetic lost acknowledgment')
        result = self.box.deliver_one(actor='synthetic:dispatcher',
            intent_event_id='route:intent:1', routed_event_id='route:saved:1',
            observed_at_utc=NOW, deliver=fail)
        self.assertEqual(result['state'], 'ROUTING')
        self.assertIsNone(self.box.deliver_one(actor='synthetic:dispatcher',
            intent_event_id='route:intent:2', routed_event_id='route:saved:2',
            observed_at_utc=NOW, deliver=fail))
        self.assertEqual(len(calls), 1)

    def test_block_and_reopen_preserve_history(self):
        blocked = self.move('BLOCKED', 1, blocker='Destination unavailable',
                            reopen_trigger='Authenticated destination is readable')
        self.assertEqual(blocked['state'], 'BLOCKED')
        reopened = self.move('RECORDED', 2, evidence_ref='evidence:new-access')
        self.assertEqual(reopened['state'], 'RECORDED')
        self.assertEqual(len(reopened['events']), 3)

    def test_duplicate_record_and_conflicting_finding_binding(self):
        duplicate = self.box.record(self.value, event_id='record:other',
            actor='maintenance', observed_at_utc=NOW)
        self.assertEqual(duplicate['handoff_id'], self.recorded['handoff_id'])
        with self.assertRaises(HandoffHold):
            self.box.record(replace(self.value, next_action='Different action'),
                event_id='record:conflict', actor='maintenance', observed_at_utc=NOW)

    def test_invalid_state_skip_is_held(self):
        with self.assertRaises(HandoffHold):
            self.move('ACCEPTED', 1, evidence_ref='task:acceptance:1')

    def test_receipt_states_and_reopening_require_evidence(self):
        self.move('ROUTING', 1)
        with self.assertRaises(ValueError):
            self.move('ROUTED', 2)
        routed = self.move('ROUTED', 3, evidence_ref='github:delivery:1')
        self.assertEqual(routed['state'], 'ROUTED')

        second = self.box.record(replace(self.value, finding_id='NXS-FINDING-TWO'),
            event_id='record:two', actor='maintenance', observed_at_utc=NOW)
        self.box.transition(second['handoff_id'], event_id='block:two',
            to_state='BLOCKED', actor='maintenance', observed_at_utc=NOW,
            blocker='Missing access', reopen_trigger='Access evidence exists')
        with self.assertRaises(ValueError):
            self.box.transition(second['handoff_id'], event_id='reopen:two',
                to_state='RECORDED', actor='maintenance', observed_at_utc=NOW)

    def test_restart_reads_same_actionable_state(self):
        reopened = HandoffOutbox(self.path, 'synthetic:worker:one')
        pending = reopened.pending(destination=self.value.destination)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['state'], 'RECORDED')

    def test_wrong_outbox_identity_is_held(self):
        with self.assertRaises(HandoffHold):
            HandoffOutbox(self.path, 'synthetic:other')


if __name__ == '__main__':
    unittest.main()
