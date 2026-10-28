"""Synthetic REST-shaped integration; no network or live provider writes."""
import copy
import json
import unittest
from urllib.parse import parse_qs, urlsplit

from nexus_sandbox.audit_checkpoint_transport import AuditCheckpointTransport, canonical
from nexus_sandbox.checkpoint_json import CheckpointAdapter, encode
from nexus_sandbox.notion_checkpoint_api import NotionCheckpointAPI
from nexus_sandbox.processing_pipeline import Receipt, STAGES, run_resumable

PAGE = '00000000000000000000000000000001'
TABLE = '00000000000000000000000000000002'


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.binding = dict(run_id='synthetic-job', source_id='synthetic-source',
            source_sha256='a'*64, destination_id=PAGE, policy_revision='synthetic-policy',
            code_revision='synthetic-code', schema_version=1)
        self.initial = encode(dict(binding=self.binding, receipts=(), pending=None), self.binding)
        event = dict(event_type='NXS_CHECKPOINT_V1', run_id=self.binding['run_id'],
            page_id=PAGE, sequence=0, previous=None, checkpoint=self.initial)
        self.blocks = [dict(object='block', id=TABLE, type='table', has_children=True,
            archived=False, in_trash=False, parent=dict(type='page_id', page_id=PAGE),
            table=dict(table_width=1, has_column_header=False, has_row_header=False)),
            self.code(4, canonical(event))]
        self.rows = [dict(object='block', id=f'{3:032x}', type='table_row',
            has_children=False, archived=False, in_trash=False,
            parent=dict(type='block_id', block_id=TABLE), table_row=dict(cells=[[]]))]
        self.requests = []
        self.lose_ack = False
        self.effects = []

    def code(self, number, text):
        return dict(object='block', id=f'{number:032x}', type='code', has_children=False,
            archived=False, in_trash=False, parent=dict(type='page_id', page_id=PAGE),
            code=dict(language='json', rich_text=[dict(type='text', plain_text=text,
                text=dict(content=text))]))

    def request(self, method, path, payload):
        self.requests.append((method, path, copy.deepcopy(payload)))
        if method == 'PATCH':
            self.assertEqual(path, '/v1/blocks/'+PAGE+'/children')
            self.assertEqual(len(payload['children']), 1)
            child = payload['children'][0]
            text = ''.join(r['text']['content'] for r in child['code']['rich_text'])
            self.blocks.append(self.code(100+len(self.blocks), text))
            if self.lose_ack:
                self.lose_ack = False
                raise TimeoutError('synthetic lost acknowledgment')
            return dict(object='list', results=[copy.deepcopy(self.blocks[-1])])
        self.assertEqual(method, 'GET')
        if path == '/v1/pages/'+PAGE:
            return dict(object='page', id=PAGE, archived=False, in_trash=False)
        parsed = urlsplit(path)
        if parsed.path == '/v1/blocks/'+TABLE+'/children':
            return dict(object='list', results=copy.deepcopy(self.rows), has_more=False, next_cursor=None)
        self.assertEqual(parsed.path, '/v1/blocks/'+PAGE+'/children')
        # Keep the table and checkpoint enrollment on separate root pages.
        later = 'start_cursor' in parse_qs(parsed.query)
        return dict(object='list', results=copy.deepcopy(self.blocks[1:] if later else self.blocks[:1]),
            has_more=not later, next_cursor=None if later else 'remaining')

    def transport(self, enabled=True, max_pages=10):
        api = NotionCheckpointAPI(PAGE, self.request, write_enabled=enabled, max_pages=max_pages)
        return AuditCheckpointTransport(PAGE, self.binding, api.fetch_page, api.append_text)

    def run_pipeline(self, transport):
        adapter = CheckpointAdapter(self.binding, transport.read, transport.save)
        def executor(stage):
            def execute(prior):
                self.effects.append(stage)
                return Receipt(self.binding['run_id'], stage, True, ('synthetic-evidence',))
            return execute
        return run_resumable(self.binding, {s: executor(s) for s in STAGES},
            adapter.save, adapter.read, lambda *_: None)

    def patches(self):
        return [r for r in self.requests if r[0] == 'PATCH']

    def test_full_pipeline_and_fresh_completed_resume_with_table_pagination(self):
        self.assertEqual(self.run_pipeline(self.transport()).status, 'COMPLETE')
        self.assertEqual(self.effects, list(STAGES))
        self.assertEqual(len(self.patches()), 14)
        self.assertEqual(self.run_pipeline(self.transport()).status, 'COMPLETE')
        self.assertEqual(self.effects, list(STAGES))
        self.assertEqual(len(self.patches()), 14)

    def test_default_write_disabled_holds_before_any_executor_or_patch(self):
        self.assertEqual(self.run_pipeline(self.transport(enabled=False)).status, 'BLOCKED')
        self.assertEqual(self.effects, [])
        self.assertEqual(self.patches(), [])

    def test_bad_table_parent_blocks_before_any_effect(self):
        self.rows[0]['parent']['block_id'] = f'{99:032x}'
        self.assertEqual(self.run_pipeline(self.transport()).status, 'BLOCKED')
        self.assertEqual(self.effects, [])
        self.assertEqual(self.patches(), [])

    def test_shared_request_budget_blocks_before_any_effect(self):
        self.assertEqual(self.run_pipeline(self.transport(max_pages=2)).status, 'BLOCKED')
        self.assertEqual(self.effects, [])
        self.assertEqual(self.patches(), [])

    def test_lost_append_ack_requires_observation_and_never_replays_effect(self):
        self.lose_ack = True
        self.assertEqual(self.run_pipeline(self.transport()).status, 'BLOCKED')
        self.assertEqual(len(self.patches()), 1)
        self.assertEqual(self.effects, [])
        fresh = self.transport()
        pending = CheckpointAdapter(self.binding, fresh.read, fresh.save).read(self.binding['run_id'])
        self.assertEqual(pending['pending'], STAGES[0])
        self.assertEqual(self.run_pipeline(self.transport()).status, 'BLOCKED')
        self.assertEqual(len(self.patches()), 1)
        self.assertEqual(self.effects, [])

    def test_readback_corruption_blocks_and_does_not_repeat_append(self):
        original = self.request
        def corrupt(method, path, payload):
            result = original(method, path, payload)
            if method == 'PATCH':
                self.blocks[-1]['parent']['page_id'] = f'{99:032x}'
            return result
        api = NotionCheckpointAPI(PAGE, corrupt, write_enabled=True)
        transport = AuditCheckpointTransport(PAGE, self.binding, api.fetch_page, api.append_text)
        self.assertEqual(self.run_pipeline(transport).status, 'BLOCKED')
        self.assertEqual(len(self.patches()), 1)
        self.assertEqual(self.effects, [])
        self.assertEqual(self.run_pipeline(self.transport()).status, 'BLOCKED')
        self.assertEqual(len(self.patches()), 1)
