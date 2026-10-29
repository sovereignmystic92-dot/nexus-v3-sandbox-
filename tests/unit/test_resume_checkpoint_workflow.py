"""Offline tests for the explicit read-only workflow entrypoint."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from nexus_sandbox.checkpoint_json import encode
from nexus_sandbox.processing_pipeline import Receipt, STAGES

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'resume_checkpoint_workflow', ROOT / 'tools/resume_checkpoint_workflow.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

BINDING = dict(run_id='offline-resume', source_id='synthetic:source',
               source_sha256=hashlib.sha256(b'offline').hexdigest(),
               destination_id='synthetic:destination', policy_revision='offline',
               code_revision='synthetic', schema_version=1)


def cp(n=0, pending=None):
    receipts = tuple(Receipt(BINDING['run_id'], stage, True, ('synthetic:verified',))
                     for stage in STAGES[:n])
    return encode(dict(binding=BINDING, receipts=receipts, pending=pending), BINDING)


class WorkflowEntryTests(unittest.TestCase):
    def test_duplicate_host_binding_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);b=root/'binding.json';c=root/'checkpoint.json'
            b.write_text(json.dumps(BINDING).replace('"run_id":','"run_id":"private-wrong-job","run_id":',1))
            c.write_text(cp(7));output=StringIO()
            with redirect_stdout(output):
                code=module.main(['--binding',str(b),'--checkpoint',str(c),'--inventory-complete','--authority-verified'])
            self.assertEqual(code,2)
            self.assertEqual(json.loads(output.getvalue())['status'],'BLOCKED')
            self.assertNotIn('private-wrong-job',output.getvalue())
    def invoke(self, checkpoint, *, inventory=True, authority=True, binding=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            b, c = root/'binding.json', root/'checkpoint.json'
            b.write_text(json.dumps(BINDING if binding is None else binding))
            c.write_text(checkpoint)
            args = ['--binding', str(b), '--checkpoint', str(c)]
            if inventory:
                args += ['--inventory-complete']
            if authority:
                args += ['--authority-verified']
            output = StringIO()
            with redirect_stdout(output):
                exit_code = module.main(args)
            return exit_code, json.loads(output.getvalue())

    def test_completed_success_no_execution(self):
        code, result = self.invoke(cp(7))
        self.assertEqual(code, 0)
        self.assertEqual(result['status'], 'COMPLETE')
        self.assertFalse(result['automatic_execution'])
        self.assertEqual(result['provider_writes'], 0)

    def test_initial_checkpoint_is_not_execution_permission(self):
        code, result = self.invoke(cp())
        self.assertEqual(code, 2)
        self.assertEqual(result['status'], 'READY_FOR_GATED_EXECUTOR')
        self.assertEqual(result['pending'], STAGES[0])

    def test_pending_never_replayed(self):
        code, result = self.invoke(cp(3, STAGES[3]))
        self.assertEqual(code, 2)
        self.assertEqual(result['next_action'], 'OBSERVE_DESTINATION_AND_RECONCILE')

    def test_authority_missing_fails_closed(self):
        self.assertEqual(self.invoke(cp(7), authority=False)[1]['status'], 'BLOCKED')

    def test_inventory_missing_fails_closed(self):
        self.assertEqual(self.invoke(cp(7), inventory=False)[1]['status'], 'BLOCKED')

    def test_malformed_checkpoint_blocks(self):
        self.assertEqual(self.invoke('{invalid')[1]['status'], 'BLOCKED')

    def test_misbound_checkpoint_blocks(self):
        other = dict(BINDING, run_id='different')
        self.assertEqual(self.invoke(cp(), binding=other)[1]['status'], 'BLOCKED')

    def test_repeated_evaluations_have_no_side_effects(self):
        first = self.invoke(cp(2, STAGES[2]))
        second = self.invoke(cp(2, STAGES[2]))
        self.assertEqual(first, second)
        self.assertEqual(second[1]['provider_writes'], 0)


if __name__ == '__main__':
    unittest.main()

