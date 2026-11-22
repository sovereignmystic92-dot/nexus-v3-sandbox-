"""Synthetic versioned service and private-IPC tests; no authenticated grants."""
import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from nexus_sandbox.source_connection_plan import prepare_connection_plan
from nexus_sandbox.transcript_ingestion_gate import prepare_transcript
from nexus_sandbox.transcript_supervised_cli import _read_line
from nexus_sandbox.versioned_custody_dispatcher import HEAD_SCHEMA, VersionedCustodyDispatcher
from supervised_test_support import make_gate


class Service:
    def __init__(self, key='synthetic-key'):
        self.files = {'synthetic-head': [json.dumps(dict(schema=HEAD_SCHEMA,
            key=key, head=None)).encode(), 0]}
        self.calls = []
        self.race = False
        self.timeout = False

    def request(self, op, data):
        self.calls.append((op, copy.deepcopy(data)))
        if op == 'store_read':
            content, version = self.files[data['reference']]
            return dict(reference=data['reference'], version=version,
                        content_b64=base64.b64encode(content).decode())
        if op == 'store_create':
            reference = 'synthetic-object-' + str(len(self.files))
            self.files[reference] = [base64.b64decode(data['content_b64']), 0]
            return dict(reference=reference)
        if op == 'store_replace':
            prior = self.files[data['reference']]
            if self.race:
                prior[1] += 1
            if data['expected_current_version'] != prior[1]:
                return dict(status='CONFLICT')
            prior[:] = [base64.b64decode(data['content_b64']), prior[1] + 1]
            if self.timeout:
                raise TimeoutError('synthetic committed replacement with lost acknowledgement')
            return dict(status='UPDATED', reference=data['reference'], version=prior[1])
        raise AssertionError(op)


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.service = Service()
        self.adapter = VersionedCustodyDispatcher('synthetic-key', 'synthetic-head', self.service.request)
        self.new = dict(generation=1, reference='synthetic-object', sha256='a' * 64)

    def test_fresh_version_is_used_and_pointer_readback_matches(self):
        self.assertIsNone(self.adapter.head('synthetic-key'))
        self.assertTrue(self.adapter.cas('synthetic-key', None, self.new))
        self.assertEqual(self.adapter.head('synthetic-key'), self.new)
        self.assertFalse(self.adapter.cas('synthetic-key', None, self.new))
        writes = [data for op, data in self.service.calls if op == 'store_replace']
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0]['expected_current_version'], 0)

    def test_competing_service_version_returns_conflict_without_retry(self):
        self.service.race = True
        self.assertFalse(self.adapter.cas('synthetic-key', None, self.new))
        self.assertIsNone(self.adapter.head('synthetic-key'))
        self.assertEqual(sum(op == 'store_replace' for op, _ in self.service.calls), 1)

    def test_uncertain_replacement_is_not_a_conflict_or_retry(self):
        self.service.timeout = True
        with self.assertRaises(TimeoutError):
            self.adapter.cas('synthetic-key', None, self.new)
        self.assertEqual(self.adapter.head('synthetic-key'), self.new)
        self.assertEqual(sum(op == 'store_replace' for op, _ in self.service.calls), 1)

    def test_retained_objects_have_no_replacement_path(self):
        reference = self.adapter.retain(b'synthetic immutable bytes')
        self.assertEqual(self.adapter.read(reference), b'synthetic immutable bytes')
        self.assertEqual([op for op, _ in self.service.calls], ['store_create', 'store_read'])
        with self.assertRaises(ValueError):
            self.adapter.read('synthetic-head')

    def test_wrong_identity_or_boolean_version_rejected(self):
        for bad in (dict(reference='wrong', version=0, content_b64='eA=='),
                    dict(reference='synthetic-head', version=True, content_b64='eA==')):
            with self.subTest(bad=bad):
                adapter = VersionedCustodyDispatcher('synthetic-key', 'synthetic-head', lambda *args: bad)
                with self.assertRaises(ValueError):
                    adapter.head('synthetic-key')

    def test_malformed_head_duplicate_keys_and_nonfinite_are_rejected(self):
        for content in (b'{"schema":1,"schema":2}', b'{"head":NaN}',
                        b'{"schema":"nexus.versioned-custody-head.v1","key":"wrong","head":null}'):
            with self.subTest(content=content):
                self.service.files['synthetic-head'][0] = content
                with self.assertRaises(ValueError):
                    self.adapter.head('synthetic-key')

    def test_wrong_key_generation_or_head_object_identity_rejected(self):
        with self.assertRaises(ValueError):
            self.adapter.head('another-key')
        with self.assertRaises(ValueError):
            self.adapter.cas('synthetic-key', None, dict(self.new, generation=2))
        adapter = VersionedCustodyDispatcher('synthetic-key', 'synthetic-head',
                                             lambda *args: dict(reference='synthetic-head'))
        with self.assertRaises(ValueError):
            adapter.retain(b'synthetic')


class ConnectedCustodyCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        prepared = prepare_transcript('SYNTHETIC private storage source. ' * 30, 256)
        supervised = dict(prepared=prepared, source_page='11111111-1111-4111-8111-111111111111',
            source_sha256=prepared['receipt']['sha256'], output_name='synthetic-output',
            analysis='Synthetic source-attributed result', expected_owner='synthetic-owner')
        supervised['analysis_gate'] = make_gate(supervised['source_page'],
            supervised['source_sha256'], supervised['output_name'], supervised['analysis'])
        envelope = dict(document_id='notion:' + supervised['source_page'],
            source_url='https://app.notion.com/p/' + supervised['source_page'].replace('-', ''),
            source_revision='synthetic-revision', transcript=''.join(prepared['chunks']),
            expected_sha256=supervised['source_sha256'])
        plan = prepare_connection_plan(envelope, mission_id='synthetic-test',
                                       code_revision='a' * 40, policy_revision='synthetic-policy')
        self.config = dict(plan=plan, consumer='csf', supervised=supervised,
                           custody_head_reference='synthetic-head')
        self.key = next(c['work_key'] for c in plan['consumers'] if c['consumer'] == 'csf')
        self.service = Service(self.key)
        self.path = self.root / 'config.json'
        self.journal = self.root / 'journal.sqlite'
        self.module, self.receipt = None, None
        self.creates = 0

    def start(self, flags=(), journal=None):
        self.path.write_text(json.dumps(self.config))
        process = subprocess.Popen([sys.executable, '-m', 'nexus_sandbox.custodied_connected_cli',
            '--config', str(self.path), '--journal', str(journal or self.journal), *flags],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / 'src')))
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
        self.addCleanup(cleanup)
        return process

    def receive(self, process):
        return json.loads(_read_line(process.stdout.fileno(), timeout=5))

    def serve(self, process, wrong_id=False, drop_replace_reply=False):
        for _ in range(150):
            message = self.receive(process)
            if message['type'] != 'request':
                process.wait(timeout=5)
                return message
            op, data = message['operation'], message['payload']
            if op.startswith('store_'):
                value = self.service.request(op, data)
                if op == 'store_replace' and drop_replace_reply:
                    process.stdin.close()
                    result = self.receive(process)
                    process.wait(timeout=5)
                    return result
            elif op == 'source_reference':
                value = self.config['plan']['source']
            elif op == 'retained_receipt':
                value = self.receipt
            elif op == 'archive_read':
                value = dict(destination=data['page_id'], source_sha256=data['source_sha256'],
                    complete=True, chunks=[dict(index=i, text=t) for i, t in
                        enumerate(self.config['supervised']['prepared']['chunks'])])
            elif op == 'cortex_get':
                value = self.module
            elif op == 'cortex_create':
                self.creates += 1
                self.module = dict(id='synthetic-module', name=data['name'],
                    owner='synthetic-owner', version=1, content=data['content'])
                value = {}
            else:
                self.fail('Unexpected private operation')
            response = dict(id=message['id'] + int(wrong_id), ok=True, value=value)
            process.stdin.write(json.dumps(response).encode() + b'\n')
            process.stdin.flush()
        self.fail('Unbounded protocol request count')

    def test_process_create_retained_receipt_reentry_and_explicit_restore(self):
        first = self.serve(self.start(('--initialize', '--allow-create')))
        self.assertEqual(first['result']['execution']['status'], 'PENDING_RECEIPT')
        self.receipt = dict(reference='synthetic-retained-receipt', content_b64=base64.b64encode(
            json.dumps(first['result']['execution']['receipt_to_retain']).encode()).decode())
        second = self.serve(self.start())
        self.assertEqual(second['result']['execution']['status'], 'CONSUMER_PERSISTENCE_READBACK_MATCHED')
        restored = self.root / 'restored.sqlite'
        third = self.serve(self.start(('--restore',), journal=restored))
        self.assertEqual(third['result']['execution']['status'], 'CONSUMER_PERSISTENCE_READBACK_MATCHED')
        self.assertEqual(self.creates, 1)
        self.assertTrue(self.journal.is_file())

    def test_default_mode_cannot_create_provider_output(self):
        result = self.serve(self.start(('--initialize',)))
        self.assertEqual(result['result']['execution']['status'], 'BLOCKED')
        self.assertEqual(self.creates, 0)

    def test_lost_replacement_reply_stops_without_provider_create(self):
        result = self.serve(self.start(('--initialize', '--allow-create')),
                            drop_replace_reply=True)
        self.assertEqual(result['type'], 'blocked')
        self.assertIsNotNone(VersionedCustodyDispatcher(self.key, 'synthetic-head',
            self.service.request).head(self.key))
        self.assertEqual(self.creates, 0)

    def test_version_conflict_stops_before_any_create(self):
        self.service.race = True
        result = self.serve(self.start(('--initialize', '--allow-create')))
        self.assertEqual(result['type'], 'blocked')
        self.assertEqual(self.creates, 0)

    def test_wrong_response_id_cannot_be_used_as_storage_evidence(self):
        result = self.serve(self.start(('--initialize', '--allow-create')), wrong_id=True)
        self.assertEqual(result['type'], 'blocked')
        self.assertEqual(self.creates, 0)

    def test_missing_gate_blocks_before_host_request_or_journal(self):
        del self.config['supervised']['analysis_gate']
        process = self.start(('--initialize', '--allow-create'))
        self.assertEqual(self.receive(process)['type'], 'blocked')
        process.wait(timeout=5)
        self.assertFalse(self.journal.exists())

    def test_valid_but_misbound_plan_blocks_before_storage_request(self):
        s = self.config['supervised']
        envelope = dict(document_id='notion:22222222-2222-4222-8222-222222222222',
            source_url='https://app.notion.com/p/22222222222242228222222222222222',
            source_revision='synthetic-revision', transcript=''.join(s['prepared']['chunks']),
            expected_sha256=s['source_sha256'])
        self.config['plan'] = prepare_connection_plan(envelope, mission_id='synthetic-test',
            code_revision='a' * 40, policy_revision='synthetic-policy')
        process = self.start(('--initialize', '--allow-create'))
        self.assertEqual(self.receive(process)['type'], 'blocked')
        process.wait(timeout=5)
        self.assertFalse(self.journal.exists())

    def test_restore_and_create_grant_are_incompatible(self):
        process = self.start(('--restore', '--allow-create'))
        self.assertEqual(self.receive(process)['type'], 'blocked')
        process.wait(timeout=5)
        self.assertFalse(self.journal.exists())


if __name__ == '__main__':
    unittest.main()
