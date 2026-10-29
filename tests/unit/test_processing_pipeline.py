from dataclasses import replace
import unittest
from nexus_sandbox.processing_pipeline import Receipt, STAGES, run


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.checkpoint = {}
        def executor(stage):
            def execute(prior):
                self.calls.append(stage)
                self.assertEqual(len(prior), STAGES.index(stage))
                return Receipt('run-one', stage, True, ('evidence:' + stage,))
            return execute
        self.executors = {s: executor(s) for s in STAGES}

    def run_pipeline(self, save=None, read=None):
        return run('run-one', self.executors,
                   save or (lambda key, receipts: self.checkpoint.update({key: receipts})),
                   read or (lambda key: self.checkpoint[key]))

    def test_automatically_continues_through_all_required_stages(self):
        result = self.run_pipeline()
        self.assertEqual(result.status, 'COMPLETE')
        self.assertEqual(tuple(self.calls), STAGES)

    def test_analyzed_is_not_complete_without_saved_output(self):
        self.executors['PERSISTED'] = lambda _: Receipt('run-one', 'PERSISTED', False, ())
        result = self.run_pipeline()
        self.assertEqual(result.status, 'INCOMPLETE')
        self.assertEqual(result.last_confirmed, 'ANALYZED')
        self.assertNotIn('REGISTERED', self.calls)

    def test_wrong_run_stage_and_truthy_flags_hold(self):
        for receipt in (Receipt('wrong', STAGES[0], True, ('e',)),
                        Receipt('run-one', 'ANALYZED', True, ('e',)),
                        Receipt('run-one', STAGES[0], 1, ('e',))):
            self.executors[STAGES[0]] = lambda _, receipt=receipt: receipt
            self.assertEqual(self.run_pipeline().status, 'INCOMPLETE')

    def test_checkpoint_write_failure_stops_without_retry(self):
        def failed(*_):
            raise OSError('private detail')
        result = self.run_pipeline(save=failed)
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(self.calls, [STAGES[0]])
        self.assertNotIn('private detail', repr(result))

    def test_stale_checkpoint_readback_stops_completion(self):
        result = self.run_pipeline(read=lambda _: ())
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.next_stage, STAGES[0])

    def test_final_readback_failure_never_reports_complete(self):
        self.executors['READBACK_VERIFIED'] = lambda _: Receipt(
            'run-one', 'READBACK_VERIFIED', False, ('missing-output',))
        self.assertEqual(self.run_pipeline().status, 'INCOMPLETE')

    def test_missing_executor_rejected_before_any_work(self):
        del self.executors['REGISTERED']
        with self.assertRaises(ValueError):
            self.run_pipeline()
        self.assertEqual(self.calls, [])

    def test_failed_executor_stops_without_blind_retry(self):
        def failed(_):
            raise TimeoutError()
        self.executors['PERSISTED'] = failed
        result = self.run_pipeline()
        self.assertEqual(result.status, 'BLOCKED')
        self.assertEqual(result.next_stage, 'PERSISTED')
        self.assertEqual(len(result.receipts), 4)
