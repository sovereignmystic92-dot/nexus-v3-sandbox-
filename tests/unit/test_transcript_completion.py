import copy
from dataclasses import replace
import unittest

from nexus_sandbox.processing_pipeline import Receipt, STAGES
from nexus_sandbox.transcript_completion import (
    OutputSnapshot, SourceSnapshot, TranscriptPlan, run_transcript,
    source_digest, verify_completion,
)


class TranscriptCompletionTests(unittest.TestCase):
    def setUp(self):
        self.source = SourceSnapshot('synthetic:source', 'synthetic:archive',
                                    (('one', 'Beginning. '), ('two', 'Middle. End.')), True)
        self.plan = TranscriptPlan(self.source, ('synthetic:output',), 'synthetic:outputs')
        self.output = OutputSnapshot('synthetic:output', 'synthetic:outputs',
                                     self.source.page_id, source_digest(self.source), 'ARCHIVED', True)

    def check(self, source=None, output=None, plan=None):
        return verify_completion(plan or self.plan,
                                 lambda _: source if source is not None else self.source,
                                 lambda _: output if output is not None else self.output)

    def test_complete_full_text(self):
        self.assertEqual(self.check(), source_digest(self.source))

    def test_same_word_count_changed_interior_holds(self):
        source = replace(self.source, segments=(('one', 'Beginning. '), ('two', 'Wrong. End.')))
        with self.assertRaises(ValueError):
            self.check(source=source)

    def test_missing_reordered_duplicate_or_changed_boundary_holds(self):
        variants = [self.source.segments[:1], self.source.segments[::-1],
                    (self.source.segments[0], self.source.segments[0]),
                    (('one', 'Beginning.'), ('two', ' Middle. End.'))]
        for segments in variants:
            with self.subTest(segments=segments), self.assertRaises(ValueError):
                self.check(source=replace(self.source, segments=segments))

    def test_partial_or_wrong_source_identity_holds(self):
        for change in ({'complete': False}, {'complete': 1}, {'page_id': 'wrong'}, {'parent_id': 'wrong'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check(source=replace(self.source, **change))

    def test_stale_status_hash_link_parent_identity_or_partial_output_holds(self):
        for change in ({'archival_status': 'INCOMPLETE'}, {'source_sha256': '0' * 64},
                       {'source_id': 'wrong'}, {'page_id': 'wrong'},
                       {'parent_id': 'wrong'}, {'complete': False}, {'complete': 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check(output=replace(self.output, **change))

    def test_empty_duplicate_or_malformed_expected_inventory_holds(self):
        for plan in (replace(self.plan, output_ids=()),
                     replace(self.plan, output_ids=('same', 'same')),
                     replace(self.plan, source=replace(self.source, segments=())),
                     replace(self.plan, source=replace(self.source, segments=(('one',),)))):
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                self.check(plan=plan)

    def pipeline(self, fetch_source=None, output=None, checkpoint_bad=False):
        self.called = []
        self.store = {}
        def executor(stage):
            def execute(prior):
                self.called.append(stage)
                return Receipt('synthetic:run', stage, True, ('synthetic:evidence',))
            return execute
        def save(run_id, receipts):
            self.store[run_id] = copy.deepcopy(receipts)
        return run_transcript('synthetic:run', self.plan,
                              {stage: executor(stage) for stage in STAGES}, save,
                              lambda run_id: () if checkpoint_bad else copy.deepcopy(self.store[run_id]),
                              fetch_source or (lambda _: self.source),
                              lambda _: output if output is not None else self.output)

    def test_pipeline_complete_with_fresh_source_reads(self):
        reads = []
        def fetch(page_id):
            reads.append(page_id)
            return self.source
        result = self.pipeline(fetch_source=fetch)
        self.assertEqual(result.status, 'COMPLETE')
        self.assertEqual(reads, [self.source.page_id] * 2)
        self.assertIn('supplied-text-sha256:' + source_digest(self.source), result.receipts[-1].evidence_refs)

    def test_initial_source_failure_prevents_analysis(self):
        result = self.pipeline(fetch_source=lambda _: replace(self.source, complete=False))
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.next_stage, 'SOURCE_PRESERVED')
        self.assertEqual(self.called, ['SOURCE_PRESERVED'])

    def test_source_changed_after_analysis_blocks_completion(self):
        reads = iter([self.source, replace(self.source, segments=(('one', 'changed'),))])
        result = self.pipeline(fetch_source=lambda _: next(reads))
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.last_confirmed, 'REGISTERED')
        self.assertEqual(result.next_stage, 'READBACK_VERIFIED')

    def test_stale_output_blocks_completion_and_preserves_checkpoint(self):
        result = self.pipeline(output=replace(self.output, archival_status='INCOMPLETE'))
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.last_confirmed, 'REGISTERED')
        self.assertEqual(len(self.store['synthetic:run']), 6)

    def test_read_failure_and_checkpoint_failure_hold(self):
        def fail(_):
            raise OSError('synthetic unavailable')
        self.assertEqual(self.pipeline(fetch_source=fail).status, 'BLOCKED')
        self.assertEqual(self.pipeline(checkpoint_bad=True).status, 'BLOCKED')


if __name__ == '__main__':
    unittest.main()
