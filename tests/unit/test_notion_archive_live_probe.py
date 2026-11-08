import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('archive_probe',
    Path(__file__).resolve().parents[2] / 'tools/notion_archive_live_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class LiveProbeTests(unittest.TestCase):
    dest = '12345678-1234-1234-1234-123456789abc'

    def test_fixed_source_write_budget(self):
        prepared = probe.prepare_transcript(probe.RAW, 256)
        self.assertEqual(len(prepared['chunks']), 3)
        self.assertEqual(''.join(prepared['chunks']), probe.RAW)

    def test_configuration_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(probe.main(), 2)

    def test_readonly_rejects_append(self):
        c = probe.BoundClient(self.dest, 'synthetic-token', False)
        with self.assertRaises(ValueError):
            c.append(block_id=self.dest, children=[{}], position={'type':'start'})
        self.assertEqual(c.writes, 0)

    def test_foreign_paths_rejected_before_network(self):
        c = probe.BoundClient(self.dest, 'synthetic-token', True)
        for method, path in [('GET','/v1/users/me'), ('PATCH','/v1/pages/other'),
                             ('POST','/v1/pages')]:
            with self.subTest(method=method), self.assertRaises(ValueError):
                c.request(method,path)

    def test_failed_request_consumes_budget_and_sanitizes(self):
        c = probe.BoundClient(self.dest, 'synthetic-token', True)
        with patch.object(c.opener, 'open', side_effect=RuntimeError('private-body')):
            with self.assertRaisesRegex(RuntimeError, '^provider request unavailable; reconcile before retry$'):
                c.append(block_id=self.dest, children=[{}], position={'type':'start'})
        self.assertEqual(c.writes, 1)
        with self.assertRaises(ValueError):
            c.append(block_id=self.dest, children=[{}], position={'type':'start'})

    def test_redirect_refused(self):
        with self.assertRaises(ValueError):
            probe.NoRedirect().redirect_request(None,None,None,None,None,None)


    def test_fault_driver_requires_kill_marker_and_then_recovers(self):
        import json
        import signal
        import subprocess
        modes = []
        env = {'GITHUB_REPOSITORY':'sovereignmystic92-dot/nexus-v3-sandbox-',
               'GITHUB_REF':'refs/heads/main', 'GITHUB_EVENT_NAME':'workflow_dispatch',
               'NOTION_ARCHIVE_TEST_CONFIRMED':'true',
               'NOTION_ARCHIVE_FIXTURE_ID':self.dest, 'GITHUB_RUN_ATTEMPT':'1',
               'NOTION_ARCHIVE_LOST_REPLY_CONFIRMED':'true'}
        def run(args, **kwargs):
            mode = args[-1]
            modes.append(mode)
            if mode == 'lost-reply':
                return subprocess.CompletedProcess(args, -signal.SIGKILL,
                    json.dumps({'fault':'ACK_DISCARDED_AFTER_SUCCESS','writes':1}), '')
            result = {'state':'ARCHIVE_VERIFIED', 'writes':0 if mode == 'observe' else 1}
            return subprocess.CompletedProcess(args, 0, json.dumps(result), '')
        with patch.dict(os.environ, env, clear=True), patch.object(
                probe.subprocess, 'run', side_effect=run):
            self.assertEqual(probe.main(), 0)
        self.assertEqual(modes, ['lost-reply','write','write','observe'])

    def test_rerun_never_injects_fault_or_writes(self):
        import json
        import subprocess
        modes = []
        env = {'GITHUB_REPOSITORY':'sovereignmystic92-dot/nexus-v3-sandbox-',
               'GITHUB_REF':'refs/heads/main', 'GITHUB_EVENT_NAME':'workflow_dispatch',
               'NOTION_ARCHIVE_TEST_CONFIRMED':'true',
               'NOTION_ARCHIVE_FIXTURE_ID':self.dest, 'GITHUB_RUN_ATTEMPT':'2',
               'NOTION_ARCHIVE_LOST_REPLY_CONFIRMED':'true'}
        def run(args, **kwargs):
            modes.append(args[-1])
            return subprocess.CompletedProcess(args, 0,
                json.dumps({'state':'ARCHIVE_VERIFIED','writes':0}), '')
        with patch.dict(os.environ, env, clear=True), patch.object(
                probe.subprocess, 'run', side_effect=run):
            self.assertEqual(probe.main(), 0)
        self.assertEqual(modes, ['observe']*4)

    def test_unexpected_child_failure_stops_without_retry(self):
        import subprocess
        env = {'GITHUB_REPOSITORY':'sovereignmystic92-dot/nexus-v3-sandbox-',
               'GITHUB_REF':'refs/heads/main', 'GITHUB_EVENT_NAME':'workflow_dispatch',
               'NOTION_ARCHIVE_TEST_CONFIRMED':'true',
               'NOTION_ARCHIVE_FIXTURE_ID':self.dest, 'GITHUB_RUN_ATTEMPT':'1',
               'NOTION_ARCHIVE_LOST_REPLY_CONFIRMED':'true'}
        with patch.dict(os.environ, env, clear=True), patch.object(
                probe.subprocess, 'run', return_value=subprocess.CompletedProcess(
                    [], 2, '{"result":"BLOCKED"}', '')) as runner:
            self.assertEqual(probe.main(), 2)
            self.assertEqual(runner.call_count, 1)


    def test_fault_occurs_only_after_a_new_successful_write(self):
        from types import SimpleNamespace
        for new_write in (False, True):
            client = SimpleNamespace(writes=0)
            def write(*args):
                client.writes = 1 if new_write else 0
            port = SimpleNamespace(write_chunk=write, read_archive=lambda *args: None)
            def attempt(*args, **kwargs):
                kwargs['write_chunk'](self.dest, 'source', 0, 'text')
                self.fail('fault callback must not return')
            with self.subTest(new_write=new_write), patch.dict(
                    os.environ, {'NOTION_SANDBOX_TOKEN':'synthetic-token'}), patch.object(
                    probe, 'BoundClient', return_value=client), patch.object(
                    probe, 'NotionArchivePort', return_value=port), patch.object(
                    probe.ArchiveRecoveryHost, 'attempt', side_effect=attempt), patch.object(
                    probe.os, 'write') as marker, patch.object(
                    probe.os, 'kill', side_effect=SystemExit) as kill:
                expected = SystemExit if new_write else ValueError
                with self.assertRaises(expected):
                    probe.child(self.dest, 'unused.sqlite', True, discard_reply=True)
                self.assertEqual(kill.call_count, int(new_write))
                self.assertEqual(marker.call_count, int(new_write))


if __name__ == '__main__':
    unittest.main()
