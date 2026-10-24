"""Injected cleanup I/O failures on disposable synthetic fixtures."""
import errno
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_restore_staging as fixtures
from nexus_sandbox.checkpoint_restore import cleanup_restore_staging
from nexus_sandbox.recovery_guard import cleanup_staged_inventory, restore_backup


class CleanupIOTests(unittest.TestCase):
    def setUp(self):
        fixtures.RestoreStagingTests.setUp(self)
        self.journal_before = self.j.read_bytes() if self.j.exists() else None
        self.inventory_before = self.i.read_bytes()

    def cleanup(self):
        return cleanup_restore_staging(self.j, self.i, self.copies, self.witness, self.root)

    def assert_protected(self):
        self.assertEqual(self.j.read_bytes() if self.j.exists() else None, self.journal_before)
        self.assertEqual(self.i.read_bytes(), self.inventory_before)

    def retry(self):
        self.cleanup()
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(self.cleanup(), [])
        self.assert_protected()

    def test_unlink_failure_before_removal_preserves_candidate(self):
        with patch.object(Path, 'unlink', side_effect=PermissionError(errno.EACCES, 'injected unlink failure')):
            with self.assertRaises(PermissionError): self.cleanup()
        self.assertTrue(self.staged.exists())
        self.assert_protected()
        self.retry()

    def test_uncertain_unlink_result_retries_empty_folder(self):
        original = Path.unlink
        def remove_then_fail(path, *args, **kwargs):
            original(path, *args, **kwargs)
            raise OSError(errno.EIO, 'injected error after removal')
        with patch.object(Path, 'unlink', remove_then_fail):
            with self.assertRaises(OSError): self.cleanup()
        self.assertFalse(self.staged.exists())
        self.assertTrue(self.folder.exists())
        self.assert_protected()
        self.retry()

    def test_rmdir_failure_after_file_removal_is_retryable(self):
        with patch.object(Path, 'rmdir', side_effect=PermissionError(errno.EACCES, 'injected rmdir failure')):
            with self.assertRaises(PermissionError): self.cleanup()
        self.assertFalse(self.staged.exists())
        self.assertTrue(self.folder.exists())
        self.assert_protected()
        self.retry()

    def test_uncertain_rmdir_result_is_retryable(self):
        original = Path.rmdir
        def remove_then_fail(path):
            original(path)
            raise OSError(errno.EIO, 'injected error after directory removal')
        with patch.object(Path, 'rmdir', remove_then_fail):
            with self.assertRaises(OSError): self.cleanup()
        self.assertEqual(list(self.root.iterdir()), [])
        self.assert_protected()
        self.retry()

    def test_restore_cleanup_retry_retries_failed_directory_sync_even_when_empty(self):
        with patch('nexus_sandbox.checkpoint_restore.os.fsync', side_effect=OSError(errno.EIO, 'injected sync failure')):
            with self.assertRaises(OSError): self.cleanup()
        self.assertEqual(list(self.root.iterdir()), [])
        self.assert_protected()
        with patch('nexus_sandbox.checkpoint_restore.os.fsync', wraps=os.fsync) as sync:
            self.assertEqual(self.cleanup(), [])
            self.assertEqual(sync.call_count, 1, 'Retry must sync even after previous removals emptied the root')
        self.assert_protected()

    def test_inventory_cleanup_retry_retries_failed_directory_sync_even_when_empty(self):
        # Inventory-stage maintenance requires a valid existing journal.
        backup = self.j.parent.parent / 'backup.sqlite'
        restore_backup(self.j, self.i, backup)
        self.journal_before = self.j.read_bytes()
        pending = self.i.with_name(self.i.name + '.pending-' + 'a' * 32)
        pending.write_bytes(b'Interrupted inventory staging; never adopted')
        with patch('nexus_sandbox.recovery_guard.os.fsync', side_effect=OSError(errno.EIO, 'injected sync failure')):
            with self.assertRaises(OSError): cleanup_staged_inventory(self.j, self.i)
        self.assertFalse(pending.exists())
        self.assert_protected()
        with patch('nexus_sandbox.recovery_guard.os.fsync', wraps=os.fsync) as sync:
            self.assertEqual(cleanup_staged_inventory(self.j, self.i), [])
            self.assertEqual(sync.call_count, 1, 'Inventory cleanup retry must retry the failed sync')
        self.assert_protected()
