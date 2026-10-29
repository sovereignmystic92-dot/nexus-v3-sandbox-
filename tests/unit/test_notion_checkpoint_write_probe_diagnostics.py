"""Synthetic D24 diagnostics; all requests use an in-memory Notion fixture."""
import json
import unittest

import test_notion_checkpoint_write_probe as existing


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.fixture = existing.WriteProbeTests()
        self.fixture.setUp()

    def check(self, result, mode, state, outcome, writes):
        self.assertEqual(result['execution_mode'], mode)
        self.assertEqual(result['checkpoint_state'], state)
        self.assertEqual(result['write_outcome'], outcome)
        self.assertEqual(result['writes_attempted'], writes)
        self.assertEqual(result['cp09'], 'NOT_PROVEN')
        self.assertEqual(result['bridge_activation'], 'INACTIVE')
        self.assertNotIn('secret-must-not-leak', json.dumps(result))

    def test_first_attempt_write(self):
        result = self.fixture.run_probe()
        self.assertEqual(result['result'], 'VERIFIED')
        self.check(result, 'FIRST_ATTEMPT_WRITE_ELIGIBLE',
                   'CHECKPOINT_ALREADY_PRESENT', 'ACKNOWLEDGED', 1)
        self.assertEqual([c[0] for c in self.fixture.calls],
                         ['GET', 'GET', 'PATCH', 'GET', 'GET'])

    def test_absent_checkpoint_on_rerun(self):
        result = self.fixture.run_probe(False)
        self.assertEqual(result['result'], 'BLOCKED_OBSERVE_ONLY_ABSENT')
        self.check(result, 'RERUN_OBSERVE_ONLY', 'CHECKPOINT_ABSENT', 'NOT_ATTEMPTED', 0)
        self.assertEqual(self.fixture.writes(), [])

    def test_existing_checkpoint(self):
        self.fixture.run_probe()
        result = self.fixture.run_probe(False)
        self.assertEqual(result['result'], 'VERIFIED_ALREADY_PRESENT')
        self.check(result, 'RERUN_OBSERVE_ONLY',
                   'CHECKPOINT_ALREADY_PRESENT', 'NOT_ATTEMPTED', 0)
        self.assertEqual(len(self.fixture.writes()), 1)

    def test_uncertain_acknowledgment_successful_readback(self):
        self.fixture.mode = 'lost_ack'
        result = self.fixture.run_probe()
        self.assertEqual(result['result'], 'VERIFIED_AFTER_UNCERTAIN_ACK')
        self.check(result, 'FIRST_ATTEMPT_WRITE_ELIGIBLE',
                   'CHECKPOINT_ALREADY_PRESENT', 'WRITE_OUTCOME_UNCERTAIN', 1)
        self.assertEqual(len(self.fixture.writes()), 1)
        self.assertEqual(result['reads'], 4)

    def test_incomplete_inventory(self):
        def incomplete(method, path, payload):
            response = self.fixture.request(method, path, payload)
            if method == 'GET' and '/children?' in path:
                response['has_more'] = True
                response['next_cursor'] = None
            return response
        result = existing.probe.probe(incomplete, '123', 'a'*40, allow_write=True)
        self.assertEqual(result['result'], 'BLOCKED_BEFORE_WRITE')
        self.check(result, 'FIRST_ATTEMPT_WRITE_ELIGIBLE', 'UNKNOWN', 'NOT_ATTEMPTED', 0)
        self.assertEqual(self.fixture.writes(), [])

    def test_mismatch_preserves_source_binding(self):
        self.fixture.run_probe()
        result = existing.probe.probe(self.fixture.request, '123', 'b'*40, allow_write=True)
        self.assertEqual(result['result'], 'BLOCKED_BEFORE_WRITE')
        self.check(result, 'FIRST_ATTEMPT_WRITE_ELIGIBLE', 'UNKNOWN', 'NOT_ATTEMPTED', 0)
        self.assertEqual(len(self.fixture.writes()), 1)

    def test_invalid_run_identity(self):
        for run in ('0', '', 'secret text', None, '1'*26):
            with self.subTest(run=run), self.assertRaises(ValueError):
                self.fixture.run_probe(run=run)
        self.assertEqual(self.fixture.calls, [])

    def test_uncertain_acknowledgment_unsuccessful_readback(self):
        self.fixture.mode = 'no_effect'
        result = self.fixture.run_probe()
        self.assertEqual(result['result'], 'BLOCKED_UNCERTAIN')
        self.check(result, 'FIRST_ATTEMPT_WRITE_ELIGIBLE',
                   'CHECKPOINT_ABSENT', 'WRITE_OUTCOME_UNCERTAIN', 1)
        self.assertEqual(result['next_action'], 'OBSERVE_ONLY_NO_BLIND_RETRY')
        self.assertEqual(self.fixture.run_probe(False)['result'], 'BLOCKED_OBSERVE_ONLY_ABSENT')
        self.assertEqual(len(self.fixture.writes()), 1)

    def test_duplicate_prevention(self):
        self.fixture.run_probe()
        for enabled in (True, False, False):
            result = self.fixture.run_probe(enabled)
            self.assertEqual(result['result'], 'VERIFIED_ALREADY_PRESENT')
            self.check(result, 'FIRST_ATTEMPT_WRITE_ELIGIBLE' if enabled else 'RERUN_OBSERVE_ONLY',
                       'CHECKPOINT_ALREADY_PRESENT', 'NOT_ATTEMPTED', 0)
        self.assertEqual(len(self.fixture.writes()), 1)

