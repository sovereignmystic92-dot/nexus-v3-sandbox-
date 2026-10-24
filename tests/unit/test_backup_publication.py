"""Backup/restore completion ordering; injected OS failures, not power loss."""
import errno
import json
import os
from pathlib import Path
import stat
import unittest
from unittest.mock import patch
import test_recovery_guard as fixture
from nexus_sandbox.recovery_guard import initialize, create_backup, restore_backup, RecoveryHold, atomic_inventory


class BackupPublicationTests(unittest.TestCase):
    def setUp(self):
        fixture.RecoveryGuardTests.setUp(self)
        initialize(self.j, self.i)
        self.backups = self.root / 'backups'
        self.backups.mkdir()
        self.backup = self.backups / 'checkpoint.sqlite'
        self.before = self.i.read_bytes()

    def is_path(self, fd, path):
        if not path.exists(): return False
        current, expected = os.fstat(fd), path.stat()
        return (current.st_dev, current.st_ino) == (expected.st_dev, expected.st_ino)

    def test_backup_file_and_directory_sync_precede_catalog_publication(self):
        events = []
        sync = os.fsync
        def observed_sync(fd):
            if self.is_path(fd, self.backup): events.append('backup_file_sync')
            elif self.is_path(fd, self.backups): events.append('backup_directory_sync')
            return sync(fd)
        def publish(path, data):
            events.append('catalog_commit')
            return atomic_inventory(path, data)
        with patch('nexus_sandbox.recovery_guard.os.fsync', observed_sync), patch('nexus_sandbox.recovery_guard.atomic_inventory', publish):
            create_backup(self.j, self.i, self.backup)
        self.assertEqual(events, ['backup_file_sync', 'backup_directory_sync', 'catalog_commit'])

    def failed_backup(self, failing_path):
        sync = os.fsync
        def fail(fd):
            if self.is_path(fd, failing_path): raise OSError(errno.EIO, 'injected backup sync error')
            return sync(fd)
        with patch('nexus_sandbox.recovery_guard.os.fsync', fail):
            with self.assertRaises(OSError): create_backup(self.j, self.i, self.backup)
        self.assertEqual(self.i.read_bytes(), self.before)
        self.assertTrue(self.backup.exists())
        self.assertEqual(json.loads(self.i.read_text())['backups'], [])

    def test_backup_file_sync_failure_does_not_register_backup(self):
        self.failed_backup(self.backup)

    def test_backup_directory_sync_failure_does_not_register_backup(self):
        self.failed_backup(self.backups)

    def test_failed_backup_is_preserved_and_retry_cannot_overwrite_it(self):
        self.failed_backup(self.backups)
        raw = self.backup.read_bytes()
        with self.assertRaises(RecoveryHold): create_backup(self.j, self.i, self.backup)
        self.assertEqual(self.backup.read_bytes(), raw)
        self.assertEqual(self.i.read_bytes(), self.before)

    def prepare_restore(self):
        create_backup(self.j, self.i, self.backup)
        self.raw = self.backup.read_bytes()
        self.registered = self.i.read_bytes()
        self.j.unlink()

    def test_restore_syncs_file_then_parent_before_success(self):
        self.prepare_restore()
        events = []
        sync = os.fsync
        def observed_sync(fd):
            if self.is_path(fd, self.j): events.append('journal_file_sync')
            elif self.is_path(fd, self.j.parent): events.append('journal_directory_sync')
            return sync(fd)
        with patch('nexus_sandbox.recovery_guard.os.fsync', observed_sync):
            result = restore_backup(self.j, self.i, self.backup)
        events.append('returned')
        self.assertEqual(events, ['journal_file_sync', 'journal_directory_sync', 'returned'])
        self.assertEqual(self.j.read_bytes(), self.raw)
        self.assertEqual(result['installation_id'], json.loads(self.registered)['installation_id'])

    def failed_restore(self, failing_path):
        self.prepare_restore()
        sync = os.fsync
        def fail(fd):
            if self.is_path(fd, failing_path): raise OSError(errno.EIO, 'injected restore sync error')
            return sync(fd)
        with patch('nexus_sandbox.recovery_guard.os.fsync', fail):
            with self.assertRaises(OSError): restore_backup(self.j, self.i, self.backup)
        self.assertEqual(self.i.read_bytes(), self.registered)
        self.assertEqual(self.backup.read_bytes(), self.raw)
        # A failed completion can leave a visible journal: preserve it, do not
        # silently overwrite it on retry. Explicit recovery is still required.
        self.assertTrue(self.j.exists())
        before_journal = self.j.read_bytes()
        with self.assertRaises(RecoveryHold): restore_backup(self.j, self.i, self.backup)
        self.assertEqual(self.j.read_bytes(), before_journal)

    def test_restore_directory_sync_error_is_not_reported_as_success(self):
        self.failed_restore(self.j.parent)

    def test_restore_file_sync_error_preserves_recovery_inputs(self):
        self.failed_restore(self.j)
