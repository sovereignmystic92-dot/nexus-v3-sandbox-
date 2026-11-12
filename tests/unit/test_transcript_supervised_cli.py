import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import unittest

from nexus_sandbox.transcript_ingestion_gate import prepare_transcript
from nexus_sandbox.transcript_supervised_cli import _read_line
from supervised_test_support import make_gate, seed_legacy


class SupervisedCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.prepared = prepare_transcript('SYNTHETIC CLI SOURCE [music]  \n')
        self.config = dict(prepared=self.prepared,
            source_page='4128c067-daa4-8132-ad77-c54099580940',
            source_sha256=self.prepared['receipt']['sha256'],
            output_name='synthetic-cli-fixture', analysis='Synthetic result',
            expected_owner='owner')
        self.config['analysis_gate'] = make_gate(self.config['source_page'],
            self.config['source_sha256'], self.config['output_name'], self.config['analysis'])
        self.config_path = self.root/'config.json'
        self.config_path.write_text(json.dumps(self.config))
        self.module = None
        self.creates = 0

    def start(self, grant=False, extra=()):
        command = [sys.executable, '-m', 'nexus_sandbox.transcript_supervised_cli',
                   '--config', str(self.config_path), '--journal', str(self.root/'run.sqlite')]
        if grant:
            command.append('--allow-create')
        command.extend(extra)
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src'))
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=env)
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
        self.addCleanup(cleanup)
        return process

    def receive(self, process):
        ready, _, _ = select.select([process.stdout], [], [], 5)
        self.assertTrue(ready, 'bounded protocol response required')
        raw = process.stdout.readline()
        self.assertTrue(raw)
        return json.loads(raw)

    def answer(self, process, message, value, **overrides):
        response = dict(id=message['id'], ok=True, value=value)
        response.update(overrides)
        process.stdin.write(json.dumps(response).encode()+b'\n')
        process.stdin.flush()

    def serve(self, process, drop_create_reply=False):
        for _ in range(8):
            message = self.receive(process)
            if message['type'] != 'request':
                process.wait(timeout=5)
                return message
            op, data = message['operation'], message['payload']
            if op == 'archive_read':
                value = dict(destination=data['page_id'], source_sha256=data['source_sha256'],
                             complete=True, chunks=[dict(index=0,text=self.prepared['chunks'][0])])
            elif op == 'cortex_get':
                value = self.module
            elif op == 'cortex_create':
                self.creates += 1
                self.module = dict(id='module_cli', name=data['name'],
                    content=data['content'], owner='owner', version=1)
                value = {}
                if drop_create_reply:
                    process.stdin.close()
                    result = self.receive(process)
                    process.wait(timeout=5)
                    return result
            else:
                self.fail('unknown operation')
            self.answer(process, message, value)
        self.fail('protocol request bound exceeded')

    def test_real_process_create_and_reopen_replay(self):
        first = self.serve(self.start(grant=True))
        self.assertEqual(first['result']['create_requests'], 1)
        second = self.serve(self.start())
        self.assertEqual(second['result']['handoff']['status'], 'READBACK_MATCHED')
        self.assertEqual(second['result']['create_requests'], 0)
        self.assertEqual(self.creates, 1)

    def test_lost_reply_reopen_reconciles_committed_output(self):
        first = self.serve(self.start(grant=True), drop_create_reply=True)
        self.assertEqual(first['result']['handoff']['status'], 'BLOCKED')
        second = self.serve(self.start(grant=True))
        self.assertEqual(second['result']['handoff']['status'], 'READBACK_MATCHED')
        self.assertEqual(self.creates, 1)

    def test_wrong_response_identity_stops_before_create(self):
        process = self.start(grant=True)
        message = self.receive(process)
        self.answer(process, message, {}, id=message['id']+1)
        self.assertEqual(self.receive(process)['type'], 'blocked')
        process.wait(timeout=5)
        self.assertEqual(self.creates, 0)

    def test_failed_host_response_is_not_absence(self):
        process = self.start(grant=True)
        message = self.receive(process)
        self.answer(process, message, None, ok=False)
        self.assertEqual(self.receive(process)['type'], 'blocked')
        process.wait(timeout=5)

    def test_extra_config_fields_stop_before_host_access(self):
        self.config['allow_create'] = True
        self.config_path.write_text(json.dumps(self.config))
        process = self.start()
        self.assertEqual(self.receive(process)['type'], 'blocked')
        process.wait(timeout=5)

    def test_default_is_readonly(self):
        result = self.serve(self.start())
        self.assertEqual(result['result']['handoff']['status'], 'BLOCKED')
        self.assertEqual(self.creates, 0)

    def test_missing_gate_stops_before_requests_and_journal(self):
        del self.config['analysis_gate']
        self.config_path.write_text(json.dumps(self.config))
        process = self.start(grant=True)
        self.assertEqual(self.receive(process)['type'], 'blocked')
        process.wait(timeout=5)
        self.assertFalse((self.root/'run.sqlite').exists())
        self.assertEqual(self.creates, 0)

    def test_malformed_or_missing_domain_blocks_before_requests(self):
        self.config['analysis_gate']['report']['domains'] = []
        self.config_path.write_text(json.dumps(self.config))
        process = self.start(grant=True)
        self.assertEqual(self.receive(process)['type'], 'blocked')
        process.wait(timeout=5)
        self.assertFalse((self.root/'run.sqlite').exists())

    def test_gate_change_cannot_rebind_reopened_process(self):
        self.serve(self.start(grant=True))
        self.config['analysis_gate']['report']['domains'][0]['contribution'] = 'Changed'
        self.config_path.write_text(json.dumps(self.config))
        process = self.start(grant=True)
        self.assertEqual(self.receive(process)['type'], 'blocked')
        process.wait(timeout=5)
        self.assertEqual(self.creates, 1)

    def test_legacy_exception_reconciles_existing_intent_without_create(self):
        gate = self.config.pop('analysis_gate')
        seed_legacy(self.root/'run.sqlite', **self.config)
        self.module = dict(id='legacy', name=self.config['output_name'],
            owner='owner', version=1, content=gate['report']['output_text'])
        self.config_path.write_text(json.dumps(self.config))
        result = self.serve(self.start(extra=('--reconcile-legacy-reason', 'recover',
                                            '--reconcile-legacy-evidence', 'owner:test')))
        self.assertEqual(result['result']['execution_mode'], 'LEGACY_READONLY_RECONCILIATION')
        self.assertEqual(result['result']['analysis_evidence_status'],
                         'NOT_ASSESSED_LEGACY_RECONCILIATION')
        self.assertEqual(self.creates, 0)

    def test_legacy_exception_cannot_enable_creates_or_omit_evidence(self):
        del self.config['analysis_gate']
        self.config_path.write_text(json.dumps(self.config))
        for grant, extra in ((True, ('--reconcile-legacy-reason','recover',
                                     '--reconcile-legacy-evidence','owner:test')),
                             (False, ('--reconcile-legacy-reason','recover'))):
            process = self.start(grant=grant, extra=extra)
            self.assertEqual(self.receive(process)['type'], 'blocked')
            process.wait(timeout=5)
        self.assertFalse((self.root/'run.sqlite').exists())

    def test_partial_response_cannot_stall_past_deadline(self):
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b'{"id":')
            with self.assertRaises(TimeoutError):
                _read_line(read_fd, timeout=0.02)
        finally:
            os.close(read_fd)
            os.close(write_fd)


if __name__ == '__main__':
    unittest.main()
