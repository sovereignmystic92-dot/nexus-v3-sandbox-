import multiprocessing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nexus_sandbox.fenced_reference import Boundary, Held, Stale, Stopped


def claim(path, start, results, owner):
    try:
        target = Boundary(path, 'fixture-one')
        if not start.wait(5):
            raise RuntimeError('Start signal missing')
        token = target.acquire(owner)
        results.put(('acquired', token.owner, token.generation))
    except Held:
        results.put(('held', owner))
    except Exception as exc:
        results.put(('error', type(exc).__name__))


def delayed_write(path, token, start, results):
    try:
        target = Boundary(path, 'fixture-one')
        if not start.wait(5):
            raise RuntimeError('Start signal missing')
        target.write(token, 'stale-worker')
        results.put('WRITTEN')
    except Stale:
        results.put('REJECTED')
    except Exception as exc:
        results.put(type(exc).__name__)


class FencedReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='nexus-fence-test-')
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'synthetic.sqlite'
        self.target = Boundary.initialize(self.path, 'fixture-one')

    def test_simultaneous_processes_get_exactly_one_owner(self):
        ctx = multiprocessing.get_context('spawn')
        start, results = ctx.Event(), ctx.Queue()
        children = [ctx.Process(target=claim, args=(str(self.path), start,
                    results, name)) for name in ('worker-a', 'worker-b')]
        try:
            for child in children:
                child.start()
            start.set()
            observed = [results.get(timeout=10) for _ in children]
            for child in children:
                child.join(10)
                self.assertEqual(child.exitcode, 0)
            self.assertEqual(sorted(row[0] for row in observed),
                             ['acquired', 'held'])
            self.assertEqual(self.target.snapshot()['generation'], 1)
        finally:
            for child in children:
                if child.is_alive():
                    child.terminate()
                    child.join(5)
            results.close()
            results.join_thread()

    def test_delayed_process_cannot_overwrite_after_takeover(self):
        old = self.target.acquire('worker-a')
        ctx = multiprocessing.get_context('spawn')
        start, results = ctx.Event(), ctx.Queue()
        child = ctx.Process(target=delayed_write,
                            args=(str(self.path), old, start, results))
        try:
            child.start()
            new = self.target.takeover(old.generation, 'worker-b')
            self.target.write(new, 'new-owner-output')
            start.set()
            self.assertEqual(results.get(timeout=10), 'REJECTED')
            child.join(10)
            self.assertEqual(child.exitcode, 0)
            self.assertEqual(self.target.snapshot()['payload'], 'new-owner-output')
        finally:
            if child.is_alive():
                child.terminate()
                child.join(5)
            results.close()
            results.join_thread()

    def test_fresh_handle_rejects_old_generation(self):
        old = self.target.acquire('worker-a')
        new = self.target.takeover(old.generation, 'worker-b')
        reopened = Boundary(self.path, 'fixture-one')
        with self.assertRaises(Stale):
            reopened.write(old, 'old')
        reopened.write(new, 'current')
        self.assertEqual(self.target.snapshot()['payload'], 'current')

    def test_old_owner_cannot_stop_current_owner(self):
        old = self.target.acquire('worker-a')
        new = self.target.takeover(old.generation, 'worker-b')
        with self.assertRaises(Stale):
            self.target.stop(old)
        self.target.write(new, 'still-writable')

    def test_stop_revokes_writes_and_reacquisition(self):
        token = self.target.acquire('worker-a')
        self.target.write(token, 'retained-evidence')
        self.target.stop(token)
        reopened = Boundary(self.path, 'fixture-one')
        with self.assertRaises(Stopped):
            reopened.write(token, 'must-not-appear')
        with self.assertRaises(Stopped):
            reopened.acquire('worker-b')
        state = reopened.snapshot()
        self.assertEqual(state['payload'], 'retained-evidence')
        self.assertIsNone(state['owner'])
        self.assertEqual(state['generation'], token.generation + 1)

    def test_changed_target_identity_refused(self):
        with self.assertRaises(ValueError):
            Boundary(self.path, 'another-fixture')

    def test_token_cannot_cross_target_boundary(self):
        token = self.target.acquire('worker-a')
        other = Boundary.initialize(Path(self.temp.name) / 'other.sqlite', 'other')
        other.acquire('worker-a')
        with self.assertRaises(Stale):
            other.write(token, 'wrong-target')
        self.assertEqual(other.snapshot()['payload'], '')

    def test_lost_database_does_not_reset_ownership(self):
        missing = Path(self.temp.name) / 'missing.sqlite'
        with self.assertRaises(sqlite3.OperationalError):
            Boundary(missing, 'fixture-one')
        self.assertFalse(missing.exists())

    def test_initialization_does_not_overwrite_existing_state(self):
        self.target.write(self.target.acquire('worker-a'), 'existing')
        with self.assertRaises(FileExistsError):
            Boundary.initialize(self.path, 'fixture-one')
        self.assertEqual(self.target.snapshot()['payload'], 'existing')

    def test_stale_takeover_expectation_is_rejected(self):
        old = self.target.acquire('worker-a')
        new = self.target.takeover(old.generation, 'worker-b')
        with self.assertRaises(Stale):
            self.target.takeover(old.generation, 'worker-c')
        self.assertEqual(self.target.snapshot()['generation'], new.generation)

    def test_invalid_payload_does_not_mutate(self):
        token = self.target.acquire('worker-a')
        with self.assertRaises(ValueError):
            self.target.write(token, 'x' * 16385)
        self.assertEqual(self.target.snapshot()['payload'], '')

    def test_owned_disposable_fixture_removed_after_close(self):
        with tempfile.TemporaryDirectory(prefix='nexus-fence-cleanup-') as directory:
            root = Path(directory)
            target = Boundary.initialize(root / 'fixture.sqlite', 'cleanup')
            token = target.acquire('worker')
            target.stop(token)
            self.assertTrue((root / 'fixture.sqlite').is_file())
        self.assertFalse(root.exists())


if __name__ == '__main__':
    unittest.main()
