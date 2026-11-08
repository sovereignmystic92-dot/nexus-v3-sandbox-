import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location('cross_probe',
    Path(__file__).resolve().parents[2] / 'tools/notion_archive_cross_run_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class CrossRunTests(unittest.TestCase):
    archive = '12345678-1234-1234-1234-123456789abc'
    journal = '12345678-1234-1234-1234-123456789def'
    revision = 'a' * 40

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pages = {self.archive: [], self.journal: []}
        self.count = 0
        self.lose_journal_reply = False

    def factory(self, destination, allow_write):
        client = SimpleNamespace(writes=0)
        def listing(**kw):
            assert kw['block_id'] == destination
            return {'results': copy.deepcopy(self.pages[destination]), 'has_more': False}
        def append(**kw):
            if not allow_write or client.writes:
                raise ValueError('write refused')
            client.writes += 1
            self.count += 1
            block = copy.deepcopy(kw['children'][0])
            block.update(id=f'00000000-0000-0000-0000-{self.count:012d}',
                parent={'type': 'page_id', 'page_id': destination}, has_children=False)
            pos = kw['position']
            if pos['type'] == 'start':
                self.pages[destination].insert(0, block)
            elif pos['type'] == 'end':
                self.pages[destination].append(block)
            else:
                index = next(i for i,b in enumerate(self.pages[destination])
                    if b['id'] == pos['after_block']['id'])
                self.pages[destination].insert(index+1, block)
            if destination == self.journal and self.lose_journal_reply:
                raise TimeoutError('lost reply')
        client.blocks = SimpleNamespace(children=SimpleNamespace(list=listing, append=append))
        client.list, client.append = listing, append
        return client

    def run_phase(self, phase, pin='', *, run='101', path='first.sqlite', write=True):
        return probe.probe(phase, self.archive, self.journal, pin, run, self.revision,
            str(Path(self.tmp.name) / path), self.factory, allow_write=write)

    def pause(self):
        return self.run_phase('pause')['checkpoint_sha256']

    def test_separate_run_restores_checkpoint_and_only_missing_chunks(self):
        pin = self.pause()
        self.assertEqual(len(self.pages[self.archive]), 1)
        self.assertEqual(len(self.pages[self.journal]), 1)
        result = self.run_phase('resume', pin, run='202', path='second.sqlite')
        self.assertEqual(result['result'], 'VERIFIED')
        self.assertEqual(result['archive_writes'], 2)
        self.assertEqual(result['checkpoint_writes'], 0)
        self.assertTrue((Path(self.tmp.name) / 'second.sqlite').exists())
        self.assertEqual(len(self.pages[self.archive]), 3)
        readonly = self.run_phase('resume', pin, run='202', path='third.sqlite', write=False)
        self.assertEqual(readonly['archive_writes'], 0)
        self.assertFalse((Path(self.tmp.name) / 'third.sqlite').exists())

    def test_same_run_cannot_claim_cross_run_resume(self):
        pin = self.pause()
        with self.assertRaises(ValueError):
            self.run_phase('resume', pin, path='second.sqlite')
        self.assertEqual(len(self.pages[self.archive]), 1)

    def test_wrong_or_missing_hash_blocks_before_writes(self):
        self.pause()
        for pin in ('', '0'*64):
            with self.assertRaises(ValueError):
                self.run_phase('resume', pin, run='202', path='second.sqlite')
        self.assertEqual(len(self.pages[self.archive]), 1)

    def test_changed_checkpoint_is_rejected(self):
        pin = self.pause()
        code = self.pages[self.journal][0]['code']
        payload = json.loads(probe.rich_text(code['rich_text']))
        payload['events'][2][2] = 1
        code['rich_text'] = [{'type':'text','text':{'content':probe.canonical(payload)}}]
        with self.assertRaises(ValueError):
            self.run_phase('resume', pin, run='202', path='second.sqlite')

    def test_source_destination_revision_and_history_bindings(self):
        pin = self.pause()
        original = probe.read_checkpoint(self.factory(self.journal, False), self.journal)
        prepared = probe.live.prepare_transcript(probe.live.RAW, 256)
        for key, value in [('destination',self.journal), ('source_sha256','0'*64),
                           ('code_revision','b'*40), ('events',[]), ('origin_run_id','bad')]:
            changed = copy.deepcopy(original)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                probe.validate_checkpoint(changed, probe.digest(changed), prepared,
                    self.archive, self.journal, '202', self.revision, require_other_run=True)

    def test_duplicate_checkpoint_and_repeated_pause_block(self):
        pin = self.pause()
        with self.assertRaises(ValueError):
            self.run_phase('pause', path='other.sqlite')
        self.pages[self.journal].append(copy.deepcopy(self.pages[self.journal][0]))
        with self.assertRaises(ValueError):
            self.run_phase('resume', pin, run='202', path='second.sqlite')

    def test_uncertain_checkpoint_append_is_not_retried(self):
        self.lose_journal_reply = True
        with self.assertRaises(TimeoutError):
            self.pause()
        self.assertEqual(len(self.pages[self.journal]), 1)
        self.assertEqual(len(self.pages[self.archive]), 1)
        with self.assertRaises(ValueError):
            self.run_phase('pause', path='other.sqlite')
        self.assertEqual(len(self.pages[self.journal]), 1)

    def test_missing_prior_archive_chunk_blocks_restore_retry(self):
        pin = self.pause()
        self.pages[self.archive] = []
        with self.assertRaises(ValueError):
            self.run_phase('resume', pin, run='202', path='second.sqlite')
        self.assertEqual(self.pages[self.archive], [])

    def test_restore_never_overwrites_existing_journal(self):
        self.pause()
        value = probe.read_checkpoint(self.factory(self.journal, False), self.journal)
        prepared = probe.live.prepare_transcript(probe.live.RAW, 256)
        with self.assertRaises(FileExistsError):
            probe.restore_checkpoint(Path(self.tmp.name) / 'first.sqlite', value,
                                     prepared, self.archive)


if __name__ == '__main__':
    unittest.main()
