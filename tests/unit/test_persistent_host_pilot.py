"""Single-host, multi-process synthetic journal pilot.

Two separate Python processes open the same SQLite file. The first provisions
and queues a synthetic event, the second recovers it using a local fixture
transport, and the third confirms no duplicate write. No network or credentials.
This is NOT evidence of cross-machine durability or external side effects.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from nexus_sandbox.github_cortex_event import REPOSITORY


WORKER = r'''
import json, sys
from pathlib import Path
from nexus_sandbox.cortex_adapter import MARKER, Module
from nexus_sandbox.cortex_host_transport import CortexHostTransport
from nexus_sandbox.github_cortex_runner import ExecutionRunner
from nexus_sandbox.journal_custody import inspect_journal
path, remote, phase, run_text = sys.argv[1:]
run = json.loads(run_text)
source = Module('source-id', 'Nexus Sandbox Pilot Source', 1, MARKER, ())
def read(name):
    if name == source.name:
        return dict(id=source.id, name=source.name, version=1,
                    content=source.content, dependencies=[])
    if Path(remote).exists():
        item = json.loads(Path(remote).read_text())
        if item['name'] == name:
            return item
    return None
def create(name, content, dependencies):
    if Path(remote).exists():
        raise AssertionError('Duplicate synthetic create')
    Path(remote).write_text(json.dumps(dict(id='target-id', name=name,
        version=1, content=content, dependencies=list(dependencies))))
def update(*args):
    raise AssertionError('Unexpected update')
options = dict(source=source, target_prefix='Nexus Sandbox Pilot Receipt ',
    transport=CortexHostTransport(read=read, create=create, update=update),
    observe_run=lambda *args: run, fixture_execution=True)
if phase == 'enqueue':
    runner = ExecutionRunner.initialize(path, 'pilot-identity', **options)
    result = runner.enqueue(run)
elif phase == 'recover':
    inspect_journal(Path(path), 'pilot-identity')
    runner = ExecutionRunner(path, 'pilot-identity', **options)
    result = runner.recover()
else:
    raise ValueError('Unknown phase')
print(json.dumps(result))
'''


class PersistentHostPilotTests(unittest.TestCase):
    def test_separate_process_enqueue_recover_and_no_duplicate_effect(self):
        run = dict(id=123, run_attempt=1, workflow_id=55, head_sha='a'*40,
                   conclusion='success', status='completed',
                   repository={'full_name': REPOSITORY},
                   html_url=f'https://github.com/{REPOSITORY}/actions/runs/123')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'journal.sqlite'
            remote = Path(folder) / 'synthetic-remote.json'
            root = Path(__file__).resolve().parents[2]
            env = dict(os.environ, PYTHONPATH=str(root / 'src'))
            def invoke(phase):
                result = subprocess.run(
                    [sys.executable, '-c', WORKER, str(path), str(remote),
                     phase, json.dumps(run)], cwd=root, env=env,
                    capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)
            key = invoke('enqueue')
            self.assertFalse(remote.exists())
            self.assertEqual(invoke('recover'), {key: 'VERIFIED'})
            before = remote.read_bytes()
            self.assertEqual(invoke('recover'), {})
            self.assertEqual(remote.read_bytes(), before)
            self.assertTrue(path.exists())

    def test_missing_journal_is_not_recreated_by_recovery(self):
        run = dict(id=123, run_attempt=1, workflow_id=55, head_sha='a'*40,
                   conclusion='success', status='completed',
                   repository={'full_name': REPOSITORY},
                   html_url=f'https://github.com/{REPOSITORY}/actions/runs/123')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'lost.sqlite'
            root = Path(__file__).resolve().parents[2]
            result = subprocess.run(
                [sys.executable, '-c', WORKER, str(path),
                 str(Path(folder) / 'remote.json'), 'recover', json.dumps(run)],
                cwd=root, env=dict(os.environ, PYTHONPATH=str(root / 'src')),
                capture_output=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
