"""Synthetic event-gate cases. No provider calls, credentials or listeners."""
import hashlib
import unittest

from nexus_sandbox.checkpoint_json import encode
from nexus_sandbox.processing_pipeline import Receipt, STAGES
from nexus_sandbox.recovery_trigger import EVENT_TYPE, assess_checkpoint_event

BINDING = dict(run_id='recovery-fixture-001', source_id='synthetic:source',
               source_sha256=hashlib.sha256(b'origin').hexdigest(),
               destination_id='synthetic:checkpoint', policy_revision='synthetic',
               code_revision='test', schema_version=1)
EVENT_ID = 'fixture-observation-123'


def checkpoint(n=0, pending=None):
    rows = tuple(Receipt(BINDING['run_id'], stage, True, ('synthetic:verified',))
                 for stage in STAGES[:n])
    return encode(dict(binding=BINDING, receipts=rows, pending=pending), BINDING)


def event(text, **changes):
    value = dict(event_type=EVENT_TYPE, event_id=EVENT_ID,
                 run_id=BINDING['run_id'], source_sha256=BINDING['source_sha256'],
                 checkpoint_sha256=hashlib.sha256(text.encode()).hexdigest())
    value.update(changes)
    return value


class RecoveryTriggerTests(unittest.TestCase):
    def assess(self, text, value=None, **changes):
        return assess_checkpoint_event(
            event(text) if value is None else value, text, BINDING,
            expected_event_id=EVENT_ID, inventory_complete=True,
            authority_verified=True, **changes)

    def test_initial_observation_requests_gated_executor_not_execution(self):
        text = checkpoint()
        result = self.assess(text)
        self.assertEqual(result['status'], 'READY_FOR_GATED_EXECUTOR')
        self.assertEqual(result['next_action'], 'VERIFY_PREREQUISITES_AND_SAVE_INTENT')
        self.assertTrue(result['event_accepted'])
        self.assertFalse(result['automatic_execution'])
        self.assertEqual(result['provider_writes'], 0)

    def test_uncertain_intent_is_reconcile_only(self):
        result = self.assess(checkpoint(3, STAGES[3]))
        self.assertEqual(result['status'], 'RECONCILE_ONLY')
        self.assertEqual(result['next_action'], 'OBSERVE_DESTINATION_AND_RECONCILE')

    def test_complete_does_not_restart(self):
        result = self.assess(checkpoint(7))
        self.assertEqual((result['status'], result['next_action']), ('COMPLETE', 'NO_ACTION'))

    def test_repeated_event_has_same_no_effect_output(self):
        text = checkpoint(2, STAGES[2])
        self.assertEqual(self.assess(text), self.assess(text))

    def test_wrong_run_rejected(self):
        text = checkpoint()
        self.assertEqual(self.assess(text, event(text, run_id='another'))['status'], 'BLOCKED')

    def test_untrusted_event_fields_not_accepted(self):
        text = checkpoint()
        payload = event(text)
        payload['authority_verified'] = True
        self.assertEqual(self.assess(text, payload)['next_action'], 'REJECT_EVENT')

    def test_wrong_event_id_rejected(self):
        text = checkpoint()
        self.assertEqual(self.assess(text, event(text, event_id='replayed'))['status'], 'BLOCKED')

    def test_wrong_source_digest_rejected(self):
        text = checkpoint()
        self.assertEqual(self.assess(text, event(text, source_sha256='0'*64))['status'], 'BLOCKED')

    def test_event_observation_mismatch_holds(self):
        text = checkpoint()
        result = self.assess(text, event(text, checkpoint_sha256='1'*64))
        self.assertEqual(result['next_action'], 'RECONCILE_EVENT_AND_OBSERVATION')

    def test_missing_inventory_holds(self):
        text = checkpoint()
        result = assess_checkpoint_event(event(text), text, BINDING,
              expected_event_id=EVENT_ID, inventory_complete=False, authority_verified=True)
        self.assertEqual(result['next_action'], 'OBTAIN_COMPLETE_INVENTORY')

    def test_missing_authority_holds(self):
        text = checkpoint()
        result = assess_checkpoint_event(event(text), text, BINDING,
              expected_event_id=EVENT_ID, inventory_complete=True, authority_verified=False)
        self.assertEqual(result['next_action'], 'VERIFY_CURRENT_AUTHORITY')

    def test_malformed_checkpoint_cannot_be_accepted(self):
        text = '{"invalid":'
        self.assertEqual(self.assess(text)['status'], 'BLOCKED')

    def test_boolean_proof_flags_must_be_strict(self):
        text = checkpoint()
        with self.assertRaises(ValueError):
            assess_checkpoint_event(event(text), text, BINDING,
                expected_event_id=EVENT_ID, inventory_complete=1, authority_verified=True)


if __name__ == '__main__':
    unittest.main()
