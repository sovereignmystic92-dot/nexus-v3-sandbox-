"""Concrete archive-port composition with synthetic Notion/Cortex transports."""
import copy
import json
from types import SimpleNamespace
import unittest
from uuid import uuid4

from nexus_sandbox.transcript_archived_handoff import run_archived_handoff
from nexus_sandbox.transcript_ingestion_gate import NotionArchivePort, prepare_transcript
from nexus_sandbox.transcript_live_handoff import Observed


class ArchivedHandoffTests(unittest.TestCase):
    dest = '12345678-1234-1234-1234-123456789abc'

    def setUp(self):
        self.raw = 'Exact 🛰 source >> [music]  \n' * 20
        self.prepared = prepare_transcript(self.raw, 256)
        self.sha = self.prepared['receipt']['sha256']
        self.blocks = []
        for index, chunk in enumerate(self.prepared['chunks']):
            rich = lambda text: [{'type': 'text', 'text': {'content': text}}]
            self.blocks.append({'id': str(uuid4()), 'type': 'code',
                'has_children': False, 'parent': {'type': 'page_id', 'page_id': self.dest},
                'code': {'caption': rich(json.dumps({'schema': 'nexus.notion-chunk.v1',
                    'index': index, 'source_sha256': self.sha})), 'rich_text': rich(chunk)}})
        self.source_reads = self.source_writes = self.output_reads = 0
        self.output_writes = []
        self.output = {}
        def listing(**kwargs):
            self.source_reads += 1
            self.assertEqual(kwargs, {'block_id': self.dest, 'page_size': 100})
            return {'results': copy.deepcopy(self.blocks), 'has_more': False}
        def append(**kwargs):
            self.source_writes += 1
            self.fail('archive handoff must never append source blocks')
        client = SimpleNamespace(blocks=SimpleNamespace(
            children=SimpleNamespace(list=listing, append=append)))
        self.port = NotionArchivePort(client, self.prepared, self.dest,
                                      expected_source_sha256=self.sha)

    def read_output(self, key):
        self.output_reads += 1
        return Observed(key, self.output[key]) if key in self.output else None

    def write_output(self, key, text):
        self.output_writes.append((key, text))
        self.output[key] = text

    def call(self, **changes):
        args = dict(prepared=self.prepared, notion_page_id=self.dest,
            expected_source_sha256=self.sha, read_archive=self.port.read_archive,
            cortex_module_name='synthetic-derived-output', analysis='Attributed analysis.',
            cortex_read=self.read_output, cortex_write=self.write_output,
            allow_cortex_write=True)
        args.update(changes)
        return run_archived_handoff(**args)

    def test_exact_archive_to_output_then_readonly_replay(self):
        self.assertEqual(self.call().status, 'READBACK_MATCHED')
        desired = ('NEXUS_SOURCE_PAGE=' + self.dest + '\nNEXUS_SOURCE_SHA256='
                   + self.sha + '\nAttributed analysis.')
        self.assertEqual(self.output_writes, [('synthetic-derived-output', desired)])
        self.assertEqual(self.source_reads, 3)
        self.assertEqual(self.call(allow_cortex_write=False).status, 'READBACK_MATCHED')
        self.assertEqual(len(self.output_writes), 1)
        self.assertEqual(self.source_writes, 0)

    def test_partial_or_changed_archive_never_reaches_cortex(self):
        original = copy.deepcopy(self.blocks)
        for bad in (original[:-1], []):
            self.blocks = bad
            with self.assertRaises(ValueError):
                self.call()
        self.blocks = original
        self.blocks[0]['code']['rich_text'][0]['text']['content'] += 'changed'
        with self.assertRaises(ValueError):
            self.call()
        self.assertEqual(self.output_reads, 0)
        self.assertEqual(self.output_writes, [])
        self.assertEqual(self.source_writes, 0)

    def test_incomplete_or_wrong_bound_observation_never_reaches_cortex(self):
        for observation in (None, {'complete': False},
                {'complete': True, 'destination': 'foreign',
                 'source_sha256': self.sha, 'chunks': []}):
            with self.subTest(observation=observation), self.assertRaises(ValueError):
                self.call(read_archive=lambda *args: observation)
        self.assertEqual(self.output_reads, 0)
        self.assertEqual(self.output_writes, [])

    def test_no_grant_and_invalid_grant_cannot_write(self):
        self.assertEqual(self.call(allow_cortex_write=False).status, 'BLOCKED')
        reads = self.source_reads
        for value in (1, 'true', None):
            with self.assertRaises(ValueError):
                self.call(allow_cortex_write=value)
        self.assertEqual(self.source_reads, reads)
        self.assertEqual(self.output_writes, [])

    def test_wrong_pinned_source_rejected_before_provider_calls(self):
        with self.assertRaises(ValueError):
            self.call(expected_source_sha256='0' * 64)
        self.assertEqual((self.source_reads, self.output_reads), (0, 0))

    def test_source_change_between_output_lookup_and_write_holds(self):
        def read(key):
            self.blocks = []
            return None
        result = self.call(cortex_read=read)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(self.output_writes, [])
        self.assertEqual(self.source_writes, 0)

    def test_final_source_change_blocks_despite_saved_output(self):
        def read(key):
            observed = self.read_output(key)
            if observed is not None:
                self.blocks = []
            return observed
        result = self.call(cortex_read=read)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.next_action, 'RECONCILE_ARCHIVE_AFTER_CORTEX_READBACK')
        self.assertEqual(len(self.output_writes), 1)
        self.assertEqual(self.source_writes, 0)

    def test_unknown_output_write_stops_and_conflict_never_overwrites(self):
        def uncertain(key, text):
            self.write_output(key, text)
            raise TimeoutError('synthetic lost response')
        result = self.call(cortex_write=uncertain)
        self.assertEqual(result.next_action, 'CORTEX_WRITE_OUTCOME_UNCERTAIN_RECONCILE')
        self.assertEqual(len(self.output_writes), 1)
        self.output['synthetic-derived-output'] = 'conflicting existing output'
        result = self.call()
        self.assertEqual(result.next_action, 'CORTEX_CONFLICT_RECONCILE_NO_OVERWRITE')
        self.assertEqual(len(self.output_writes), 1)


if __name__ == '__main__':
    unittest.main()
