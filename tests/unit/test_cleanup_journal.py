import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from cleanup_journal import CleanupJournal, CleanupHold


class CleanupJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.namespace = self.root / 'nexus-supervisor-test'
        self.namespace.mkdir()
        self.staging = self.namespace / 'nexus-isolated-test'
        self.staging.mkdir()
        (self.staging / 'payload').write_text('disposable fixture')
        self.path = self.root / 'journal.sqlite'
        self.ident = 'b' * 64
        self.present = True
        self.removals = 0
        self.journal = CleanupJournal.create(self.path, run_id='test-run',
            source_sha='a' * 40, container_name='nexus-acceptance-' + 'c' * 32,
            container_id=self.ident, namespace=self.namespace, staging=self.staging)

    def observe(self, binding):
        return self.ident if self.present else None

    def remove(self, binding):
        # Fresh reader sees intent durably before the callback.
        snap = CleanupJournal(self.path).snapshot()
        self.assertEqual(snap['status'], 'INTENT')
        self.present = False
        self.removals += 1

    def advance(self, journal=None, **kwargs):
        return (journal or self.journal).advance(self.observe, self.remove, **kwargs)

    def test_pending_checkpoint_is_readable_by_fresh_process(self):
        code = 'from cleanup_journal import CleanupJournal;import sys,json;print(json.dumps(CleanupJournal(sys.argv[1]).snapshot()))'
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / 'tools'))
        out = subprocess.check_output([sys.executable, '-B', '-c', code, str(self.path)],
                                      env=env, text=True, timeout=10)
        saved = json.loads(out)
        self.assertEqual(saved['next_step'], 'REMOVE_CONTAINER')
        self.assertIsNone(saved['last_verified'])
        self.assertEqual(saved['binding']['staging'], str(self.staging))

    def test_complete_and_repeat_never_remove_twice(self):
        self.assertEqual(self.advance()['next_step'], 'REMOVE_STAGING')
        self.assertEqual(self.advance()['next_step'], 'REMOVE_NAMESPACE')
        self.assertEqual(self.advance()['next_step'], 'COMPLETE')
        self.assertEqual(self.advance()['next_step'], 'COMPLETE')
        self.assertEqual(self.removals, 1)
        self.assertTrue(self.path.exists())
        self.assertFalse(self.namespace.exists())

    def test_lost_acknowledgment_records_uncertain_and_reconciles(self):
        def lost(): raise TimeoutError('ack lost')
        with self.assertRaises(CleanupHold): self.advance(after_action=lost)
        saved = CleanupJournal(self.path)
        self.assertEqual(saved.snapshot()['status'], 'UNCERTAIN')
        self.assertEqual(saved.snapshot()['next_step'], 'REMOVE_CONTAINER')
        self.assertEqual(self.advance(saved)['next_step'], 'REMOVE_STAGING')
        self.assertEqual(self.removals, 1)

    def test_process_exit_after_removal_leaves_intent_for_reprocessing(self):
        marker = self.root / 'container-present'
        marker.write_text(self.ident)
        code = '''
from cleanup_journal import CleanupJournal
from pathlib import Path
import os,sys
j=CleanupJournal(sys.argv[1]);p=Path(sys.argv[2])
def observe(binding): return p.read_text() if p.exists() else None
def remove(binding): p.unlink()
j.advance(observe,remove,after_action=lambda:os._exit(23))
'''
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / 'tools'))
        process = subprocess.run([sys.executable, '-B', '-c', code, str(self.path), str(marker)],
                                 env=env, timeout=10)
        self.assertEqual(process.returncode, 23)
        reopened = CleanupJournal(self.path)
        self.assertEqual(reopened.snapshot()['status'], 'INTENT')
        self.present = False
        self.assertEqual(self.advance(reopened)['next_step'], 'REMOVE_STAGING')
        self.assertEqual(self.removals, 0)

    def test_observation_failure_never_means_absent(self):
        def unknown(binding): raise RuntimeError('provider unavailable')
        with self.assertRaises(CleanupHold): self.journal.advance(unknown, self.remove)
        self.assertEqual(self.removals, 0)
        self.assertEqual(self.journal.snapshot()['status'], 'UNCERTAIN')
        self.assertTrue(self.staging.exists())

    def test_wrong_container_id_never_removed(self):
        with self.assertRaises(CleanupHold):
            self.journal.advance(lambda binding: 'd' * 64, self.remove)
        self.assertEqual(self.removals, 0)

    def test_replaced_staging_directory_is_preserved(self):
        self.advance()
        self.staging.rename(self.namespace / 'old-staging')
        self.staging.mkdir()
        (self.staging / 'newer-work').write_text('keep')
        with self.assertRaises(CleanupHold): self.advance()
        self.assertTrue((self.staging / 'newer-work').exists())

    def test_symlink_target_is_preserved(self):
        self.advance()
        self.staging.rename(self.namespace / 'old-staging')
        other = self.root / 'other'; other.mkdir()
        self.staging.symlink_to(other, target_is_directory=True)
        with self.assertRaises(CleanupHold): self.advance()
        self.assertTrue(other.exists())

    def test_unexpected_namespace_contents_are_preserved(self):
        self.advance(); self.advance()
        extra = self.namespace / 'unexpected'; extra.write_text('keep')
        with self.assertRaises(CleanupHold): self.advance()
        self.assertTrue(extra.exists())

    def test_journal_cannot_be_reset_or_deleted_with_targets(self):
        with self.assertRaises(FileExistsError):
            CleanupJournal.create(self.path, **self.creation_args())
        with self.assertRaises(CleanupHold):
            CleanupJournal.create(self.staging / 'bad.sqlite', **self.creation_args())

    def creation_args(self):
        return dict(run_id='test-run', source_sha='a' * 40,
                    container_name='nexus-acceptance-' + 'c' * 32, container_id=self.ident,
                    namespace=self.namespace, staging=self.staging)

    def test_storage_failure_prevents_removal(self):
        self.journal.record = lambda *args: (_ for _ in ()).throw(OSError('disk full'))
        with self.assertRaises(OSError): self.advance()
        self.assertEqual(self.removals, 0)

    def test_staging_requires_fresh_container_absence(self):
        self.advance()
        self.present = True
        with self.assertRaises(CleanupHold): self.advance()
        self.assertTrue(self.staging.exists())
