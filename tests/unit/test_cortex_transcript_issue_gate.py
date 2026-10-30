"""Synthetic event bridge boundary checks: no credentials or provider calls."""
import hashlib
import json
import unittest
from pathlib import Path
import importlib.util

script = Path(__file__).resolve().parents[2] / 'tools/cortex_transcript_issue_gate.py'
spec = importlib.util.spec_from_file_location('cortex_transcript_issue_gate', script)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def fixture():
    body = dict(schema='NEXUS_TRANSCRIPT_EVENT_V1', cortex_issue_id='issue_01synthetic',
                event_id='event_01synthetic', source_ref='synthetic:transcript:pilot1',
                source_sha256=hashlib.sha256(b'fixture').hexdigest(), event_kind='SOURCE_READY')
    return dict(action='opened',
                repository={'full_name':'sovereignmystic92-dot/nexus-v3-sandbox-'},
                sender={'login':'sovereignmystic92-dot'},
                issue=dict(number=9000, user={'login':'sovereignmystic92-dot'},
                           title='[Nexus synthetic transcript event]',
                           body=gate.PREFIX + json.dumps(body)))


class CortexIssueGateTests(unittest.TestCase):
    def test_valid_synthetic_event_is_observe_only(self):
        result = gate.inspect_issue_event(fixture())
        self.assertEqual(result['status'], 'OBSERVED')
        self.assertEqual(result['next_action'], 'INSPECT_TRANSCRIPT_PLAN_ONLY')
        self.assertEqual(result['provider_writes'], 0)
        self.assertFalse(result['automatic_execution'])

    def test_foreign_sender_denied(self):
        payload=fixture(); payload['sender']['login']='other'
        self.assertEqual(gate.inspect_issue_event(payload)['status'], 'HELD')

    def test_foreign_issue_author_denied(self):
        payload=fixture(); payload['issue']['user']['login']='other'
        self.assertEqual(gate.inspect_issue_event(payload)['status'], 'HELD')

    def test_wrong_repository_denied(self):
        payload=fixture(); payload['repository']['full_name']='another/repo'
        self.assertEqual(gate.inspect_issue_event(payload)['status'], 'HELD')

    def test_non_opened_event_denied(self):
        payload=fixture(); payload['action']='edited'
        self.assertEqual(gate.inspect_issue_event(payload)['status'], 'HELD')

    def test_real_source_denied(self):
        payload=fixture(); data=json.loads(payload['issue']['body'][len(gate.PREFIX):])
        data['source_ref']='https://example.org/real-transcript'
        payload['issue']['body']=gate.PREFIX+json.dumps(data)
        self.assertEqual(gate.inspect_issue_event(payload)['status'], 'HELD')

    def test_unexpected_authority_claim_denied(self):
        payload=fixture(); data=json.loads(payload['issue']['body'][len(gate.PREFIX):])
        data['authority_verified']=True
        payload['issue']['body']=gate.PREFIX+json.dumps(data)
        self.assertEqual(gate.inspect_issue_event(payload)['status'], 'HELD')

    def test_duplicate_field_denied(self):
        payload=fixture()
        payload['issue']['body'] = gate.PREFIX + '{"schema":"NEXUS_TRANSCRIPT_EVENT_V1","schema":"NEXUS_TRANSCRIPT_EVENT_V1"}'
        self.assertEqual(gate.inspect_issue_event(payload)['status'], 'HELD')

    def test_changed_digest_denied(self):
        payload=fixture(); data=json.loads(payload['issue']['body'][len(gate.PREFIX):])
        data['source_sha256']='not-a-hash'
        payload['issue']['body']=gate.PREFIX+json.dumps(data)
        self.assertEqual(gate.inspect_issue_event(payload)['status'], 'HELD')

    def test_unrecognized_issue_title_denied(self):
        payload=fixture(); payload['issue']['title']='ordinary issue'
        self.assertEqual(gate.inspect_issue_event(payload)['status'], 'HELD')


if __name__ == '__main__':
    unittest.main()
