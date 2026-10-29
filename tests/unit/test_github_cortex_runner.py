"""Offline host callbacks only; no service registration or network access."""
from dataclasses import asdict
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from nexus_sandbox.cortex_adapter import MARKER, Module
from nexus_sandbox.cortex_host_transport import CortexHostTransport
from nexus_sandbox.github_cortex_event import REPOSITORY
from nexus_sandbox.github_cortex_runner import ExecutionRunner


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'runner.sqlite'
        self.source = Module('source-id', 'Nexus Sandbox Runner Source', 1, MARKER, ())
        self.data = {self.source.name: self.source}
        self.writes = 0
        self.reads = 0
        self.mode = 'normal'
        self.run = dict(id=123, run_attempt=1, workflow_id=55, head_sha='a'*40,
                        conclusion='success', status='completed',
                        repository={'full_name': REPOSITORY},
                        html_url=f'https://github.com/{REPOSITORY}/actions/runs/123')
        self.observation = dict(self.run)
        self.options = dict(source=self.source, target_prefix='Nexus Sandbox Runner Receipt ',
                            transport=CortexHostTransport(read=self.read, create=self.create,
                                                          update=self.update),
                            observe_run=self.observe, fixture_execution=True)

    def observe(self, run_id, attempt):
        self.assertEqual((run_id, attempt), (123, 1))
        return self.observation

    def read(self, name):
        self.reads += 1
        if self.mode == 'read_failure':
            raise RuntimeError('secret callback detail')
        item = self.data.get(name)
        if item is None:
            return None
        value = asdict(item)
        value['dependencies'] = list(item.dependencies)
        return value

    def create(self, name, content, dependencies):
        self.writes += 1
        if self.mode != 'no_effect':
            self.data[name] = Module('target-id', name, 1,
                                     content if self.mode != 'mismatch' else MARKER,
                                     tuple(dependencies))
        if self.mode in ('lost_ack', 'no_effect'):
            raise TimeoutError('secret callback detail')

    def update(self, *args):
        raise AssertionError('Updates are outside this runner scope')

    def initialize(self):
        return ExecutionRunner.initialize(self.path, 'synthetic-journal', **self.options)

    def reopen(self):
        return ExecutionRunner(self.path, 'synthetic-journal', **self.options)

    def test_event_trigger_and_duplicate_delivery_independently_read_back(self):
        runner = self.initialize()
        self.assertEqual(runner.handle_event(self.run), 'VERIFIED')
        reads = self.reads
        self.assertEqual(runner.handle_event(self.run), 'VERIFIED')
        self.assertGreater(self.reads, reads)
        self.assertEqual(self.writes, 1)

    def test_restart_drains_durable_pending_event(self):
        key = self.initialize().enqueue(self.run)
        self.assertEqual(self.reopen().recover(), {key: 'VERIFIED'})
        self.assertEqual(self.writes, 1)

    def test_actual_process_exit_after_remote_effect_recovers_read_only(self):
        key = self.initialize().enqueue(self.run)
        remote = self.path.with_suffix('.remote.json')
        script = '''
import json, os, sys
from nexus_sandbox.cortex_adapter import Module, MARKER
from nexus_sandbox.cortex_host_transport import CortexHostTransport
from nexus_sandbox.github_cortex_runner import ExecutionRunner
source = Module('source-id', 'Nexus Sandbox Runner Source', 1, MARKER, ())
def read(name):
    if name == source.name:
        return dict(id=source.id, name=source.name, version=1, content=MARKER, dependencies=[])
    return None
def create(name, content, dependencies):
    with open(sys.argv[2], 'w') as output:
        json.dump(dict(id='target-id', name=name, version=1, content=content, dependencies=dependencies), output)
        output.flush()
        os.fsync(output.fileno())
    os._exit(17)
host = CortexHostTransport(read=read, create=create, update=lambda *args: None)
runner = ExecutionRunner(sys.argv[1], 'synthetic-journal', source=source,
    target_prefix='Nexus Sandbox Runner Receipt ', transport=host,
    observe_run=lambda *args: json.loads(sys.argv[3]), fixture_execution=True)
runner.recover()
'''
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run([sys.executable, '-c', script, str(self.path), str(remote),
                                 json.dumps(self.run)], cwd=root,
                                env=dict(os.environ, PYTHONPATH=str(root/'src')),
                                capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 17, result.stderr.decode())
        value = json.loads(remote.read_text())
        value['dependencies'] = tuple(value['dependencies'])
        self.data[value['name']] = Module(**value)
        self.assertEqual(self.reopen().recover(), {key: 'VERIFIED'})
        self.assertEqual(self.writes, 0)

    def test_lost_ack_recovery_never_repeats_write(self):
        runner = self.initialize()
        self.mode = 'lost_ack'
        self.assertEqual(runner.handle_event(self.run), 'HOLD')
        self.mode = 'normal'
        self.assertEqual(list(self.reopen().recover().values()), ['VERIFIED'])
        self.assertEqual(self.writes, 1)

    def test_uncertain_no_effect_never_blindly_retries(self):
        runner = self.initialize()
        self.mode = 'no_effect'
        self.assertEqual(runner.handle_event(self.run), 'HOLD')
        self.mode = 'normal'
        self.assertEqual(list(self.reopen().recover().values()), ['HOLD'])
        self.assertEqual(self.writes, 1)

    def test_readback_mismatch_holds(self):
        runner = self.initialize()
        self.mode = 'mismatch'
        self.assertEqual(runner.handle_event(self.run), 'HOLD')
        self.assertEqual(list(self.reopen().recover().values()), ['HOLD'])
        self.assertEqual(self.writes, 1)

    def test_forged_event_and_changed_authority_hold_without_writes(self):
        runner = self.initialize()
        forged = dict(self.run, conclusion='failure')
        with self.assertRaises(ValueError):
            runner.enqueue(forged)
        key = runner.enqueue(self.run)
        self.observation = forged
        self.assertEqual(runner.process(key), 'HOLD')
        self.assertEqual(self.writes, 0)

    def test_conflicting_duplicate_and_binding_change_rejected(self):
        runner = self.initialize()
        runner.enqueue(self.run)
        self.observation = dict(self.run, conclusion='failure')
        with self.assertRaises(ValueError):
            runner.enqueue(self.observation)
        self.options['target_prefix'] = 'Nexus Sandbox Different '
        with self.assertRaises(ValueError):
            self.reopen()
        self.assertEqual(self.writes, 0)

    def test_disabled_by_default(self):
        self.options.pop('fixture_execution')
        self.assertEqual(self.initialize().handle_event(self.run), 'DISABLED')
        self.assertEqual(self.writes, 0)

    def test_read_failure_and_source_drift_fail_closed(self):
        runner = self.initialize()
        self.mode = 'read_failure'
        self.assertEqual(runner.handle_event(self.run), 'HOLD')
        self.mode = 'normal'
        self.data[self.source.name] = Module('replacement', self.source.name, 2, MARKER, ())
        self.assertEqual(list(self.reopen().recover().values()), ['HOLD'])
        self.assertEqual(self.writes, 0)

    def test_missing_journal_and_wrong_identity_not_reinitialized(self):
        self.initialize()
        with self.assertRaises(ValueError):
            ExecutionRunner(self.path, 'wrong', **self.options)
        self.path.unlink()
        with self.assertRaises(sqlite3.OperationalError):
            self.reopen()
        self.assertFalse(self.path.exists())

    def test_lock_prevents_second_worker(self):
        runner = self.initialize()
        with open(str(self.path) + '.lock', 'r') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                runner.handle_event(self.run)
        self.assertEqual(self.writes, 0)

    def test_journal_has_private_permissions_and_no_untrusted_fields(self):
        runner = self.initialize()
        runner.enqueue(dict(self.run, token='secret-must-not-persist'))
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(b'secret-must-not-persist', self.path.read_bytes())
        with self.assertRaises(ValueError):
            runner.recover(0)
