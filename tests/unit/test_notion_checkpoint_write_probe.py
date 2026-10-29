import copy
import importlib.util
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('write_probe', ROOT/'tools/notion_checkpoint_write_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class WriteProbeTests(unittest.TestCase):
    def setUp(self):
        self.blocks = []
        self.calls = []
        self.mode = 'normal'

    def request(self, method, path, payload):
        self.calls.append((method, path, copy.deepcopy(payload)))
        if method == 'PATCH':
            self.assertEqual(path, '/v1/blocks/'+probe.AUDIT_ID+'/children')
            if self.mode != 'no_effect':
                child = copy.deepcopy(payload['children'][0])
                child.update(id=f'{2:032x}', archived=False, in_trash=False,
                    has_children=False, parent=dict(type='page_id', page_id=probe.AUDIT_ID))
                for rich in child['code']['rich_text']:
                    rich['plain_text'] = rich['text']['content']
                self.blocks.append(child)
                if self.mode == 'corrupt':
                    child['parent']['page_id'] = f'{99:032x}'
            if self.mode in ('lost_ack', 'no_effect'):
                raise TimeoutError('secret-must-not-leak')
            return dict(object='list', results=copy.deepcopy(self.blocks))
        self.assertEqual(method, 'GET')
        if path == '/v1/pages/'+probe.AUDIT_ID:
            return dict(object='page', id=probe.AUDIT_ID, archived=False, in_trash=False)
        return dict(object='list', results=copy.deepcopy(self.blocks), has_more=False, next_cursor=None)

    def run_probe(self, enabled=True, run='123'):
        return probe.probe(self.request, run, 'a'*40, allow_write=enabled)

    def writes(self):
        return [c for c in self.calls if c[0]=='PATCH']

    def test_single_marked_append_verified_and_repeat_does_not_append(self):
        result = self.run_probe()
        self.assertEqual(result['result'], 'VERIFIED')
        self.assertEqual(result['writes_attempted'], 1)
        self.assertEqual(result['reads'], 4)
        event = json.loads(self.blocks[0]['code']['rich_text'][0]['plain_text'])
        self.assertEqual(event['page_id'], probe.AUDIT_ID)
        self.assertEqual(event['sequence'], 0)
        self.assertEqual(self.run_probe()['result'], 'VERIFIED_ALREADY_PRESENT')
        self.assertEqual(len(self.writes()), 1)

    def test_observe_only_absence_makes_no_write(self):
        self.assertEqual(self.run_probe(False)['result'], 'BLOCKED_OBSERVE_ONLY_ABSENT')
        self.assertEqual(self.writes(), [])

    def test_lost_ack_observes_exact_record_without_retry(self):
        self.mode='lost_ack'
        result=self.run_probe()
        self.assertEqual(result['result'], 'VERIFIED_AFTER_UNCERTAIN_ACK')
        self.assertEqual(len(self.writes()), 1)
        self.assertEqual(self.run_probe(False)['result'], 'VERIFIED_ALREADY_PRESENT')
        self.assertEqual(len(self.writes()), 1)

    def test_uncertain_absent_write_stops_without_retry_or_secret_output(self):
        self.mode='no_effect'
        result=self.run_probe()
        self.assertEqual(result['result'], 'BLOCKED_UNCERTAIN')
        self.assertEqual(len(self.writes()), 1)
        self.assertNotIn('secret-must-not-leak', json.dumps(result))
        self.assertEqual(self.run_probe(False)['result'], 'BLOCKED_OBSERVE_ONLY_ABSENT')
        self.assertEqual(len(self.writes()), 1)

    def test_wrong_parent_after_append_blocks_without_retry(self):
        self.mode='corrupt'
        self.assertEqual(self.run_probe()['result'], 'BLOCKED_UNCERTAIN')
        self.assertEqual(len(self.writes()), 1)
        self.assertEqual(self.run_probe(False)['result'], 'BLOCKED_BEFORE_WRITE')
        self.assertEqual(len(self.writes()), 1)

    def test_incomplete_or_malformed_initial_inventory_never_appends(self):
        for body in ('{bad}', '{"unrelated":NaN}'):
            self.blocks=[dict(object='block', id=f'{2:032x}', type='code', has_children=False,
                archived=False, in_trash=False, parent=dict(type='page_id', page_id=probe.AUDIT_ID),
                code=dict(language='json', rich_text=[dict(type='text', plain_text=body,text=dict(content=body))]))]
            self.assertEqual(self.run_probe()['result'], 'BLOCKED_BEFORE_WRITE')
        self.assertEqual(self.writes(), [])

    def test_missing_confirmation_or_wrong_environment_never_loads_token(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(probe, 'NotionRequest') as client:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(probe.main(), 2)
            client.assert_not_called()

    def test_rerun_uses_observation_only(self):
        env=dict(GITHUB_REPOSITORY='sovereignmystic92-dot/nexus-v3-sandbox-',
            GITHUB_REF='refs/heads/main', GITHUB_EVENT_NAME='workflow_dispatch',
            NOTION_CHECKPOINT_TEST_CONFIRMED='true', GITHUB_RUN_ATTEMPT='2',
            NOTION_SANDBOX_TOKEN='synthetic-token', GITHUB_RUN_ID='123', GITHUB_SHA='a'*40)
        with patch.dict(os.environ, env, clear=True), patch.object(probe, 'NotionRequest') as client, patch.object(probe,'probe',return_value={'result':'VERIFIED_ALREADY_PRESENT'}) as run:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(probe.main(), 0)
            self.assertFalse(client.call_args.kwargs['write_enabled'])
            self.assertFalse(run.call_args.kwargs['allow_write'])

    def test_mismatched_existing_checkpoint_blocks_without_second_write(self):
        self.assertEqual(self.run_probe()['result'], 'VERIFIED')
        result=probe.probe(self.request, '123', 'b'*40, allow_write=True)
        self.assertEqual(result['result'], 'BLOCKED_BEFORE_WRITE')
        self.assertEqual(len(self.writes()),1)

    def test_invalid_run_and_source_rejected_without_requests(self):
        for run,sha in [('0','a'*40),('123','bad'),('secret text','a'*40)]:
            with self.assertRaises(ValueError):probe.probe(self.request,run,sha,allow_write=True)
        self.assertEqual(self.calls,[])
