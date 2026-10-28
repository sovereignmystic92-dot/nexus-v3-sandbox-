import unittest
from unittest.mock import patch
from tools.notion_checkpoint_write_probe import probe

SHA = 'a' * 40


class ProbeDiagnostics(unittest.TestCase):
    def run_case(self, events, append_error=None):
        class API:
            def __init__(self, page, request, **kwargs):
                self.fetch_page = lambda page: None
                def append(page, text):
                    request('PATCH', '/test', {})
                    if append_error:
                        raise append_error
                self.append_text = append
        class Transport:
            def __init__(self, *args):
                self.results = iter(events)
            def _events(self):
                value = next(self.results)
                if isinstance(value, Exception):
                    raise value
                return value
        with patch('tools.notion_checkpoint_write_probe.NotionCheckpointAPI', API), \
             patch('tools.notion_checkpoint_write_probe.AuditCheckpointTransport', Transport):
            return probe(lambda *args: {}, '123', SHA, allow_write=True)

    def test_failed_readback_after_ack_is_uncertain(self):
        result = self.run_case([[], ValueError('private data')])
        self.assertEqual((result['result'], result['failure_stage'], result['write_ack']),
                         ('BLOCKED_UNCERTAIN', 'READBACK', 'RECEIVED'))
        self.assertEqual(result['writes_attempted'], 1)
        self.assertNotIn('private data', str(result))

    def test_lost_response_then_absent_stays_blocked(self):
        result = self.run_case([[], []], TimeoutError('secret'))
        self.assertEqual((result['result'], result['failure_stage'], result['write_ack']),
                         ('BLOCKED_UNCERTAIN', 'READBACK', 'UNCERTAIN'))
        self.assertEqual(result['next_action'], 'OBSERVE_ONLY_NO_BLIND_RETRY')
        self.assertNotIn('secret', str(result))

    def test_incomplete_inventory_before_write(self):
        result = self.run_case([ValueError('incomplete')])
        self.assertEqual((result['result'], result['failure_stage'], result['write_ack']),
                         ('BLOCKED_BEFORE_WRITE', 'PREWRITE_OBSERVATION', 'NOT_ATTEMPTED'))
        self.assertEqual(result['writes_attempted'], 0)


if __name__ == '__main__':
    unittest.main()
