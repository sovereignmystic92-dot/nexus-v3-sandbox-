"""OS-call ordering and failure injection; not physical-power-loss proof."""
import errno
import json
import os
import stat
import unittest
from unittest.mock import patch

import test_recovery_guard as fixture
from nexus_sandbox.recovery_guard import initialize, atomic_inventory


class InventoryCommitTests(unittest.TestCase):
    def setUp(self):
        fixture.RecoveryGuardTests.setUp(self)
        initialize(self.j, self.i)
        self.worker = fixture.RecoveryGuardTests.adapter(self)

    def assert_no_transport(self):
        self.assertEqual(self.transport.reads, [])
        self.assertEqual(self.transport.writes, 0)

    def test_atomic_commit_syncs_file_then_replaces_then_syncs_directory(self):
        events = []
        sync, replace = os.fsync, os.replace
        def observed_sync(fd):
            events.append('directory_sync' if stat.S_ISDIR(os.fstat(fd).st_mode) else 'file_sync')
            return sync(fd)
        def observed_replace(*args):
            events.append('replace')
            return replace(*args)
        data = json.loads(self.i.read_text())
        with patch('nexus_sandbox.recovery_guard.os.fsync', observed_sync), patch('nexus_sandbox.recovery_guard.os.replace', observed_replace):
            atomic_inventory(self.i, data)
        self.assertEqual(events, ['file_sync', 'replace', 'directory_sync'])
        self.assertEqual(json.loads(self.i.read_text()), data)

    def test_pending_directory_sync_precedes_first_transport_access(self):
        events = []
        sync, get = os.fsync, self.transport.get
        def observed_sync(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                events.append(('directory_sync', json.loads(self.i.read_text())['state']))
            return sync(fd)
        def observed_get(name):
            events.append(('transport_read', name))
            return get(name)
        self.transport.get = observed_get
        with patch('nexus_sandbox.recovery_guard.os.fsync', observed_sync):
            result = self.worker.ensure(self.request)
        self.assertEqual(result.protocol_verdict, 'VERIFIED')
        self.assertEqual(events[0], ('directory_sync', 'operation_pending'))
        self.assertEqual(events[-1], ('directory_sync', 'ready'))

    def test_directory_sync_failure_stops_before_any_transport(self):
        sync = os.fsync
        def failing_sync(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError(errno.EIO, 'injected directory sync failure')
            return sync(fd)
        with patch('nexus_sandbox.recovery_guard.os.fsync', failing_sync):
            with self.assertRaises(OSError): self.worker.ensure(self.request)
        self.assert_no_transport()
        self.assertEqual(json.loads(self.i.read_text())['state'], 'operation_pending')

    def test_repeated_directory_sync_failure_keeps_pending_request_blocked(self):
        sync = os.fsync
        def failing_sync(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError(errno.EIO, 'persistent directory failure')
            return sync(fd)
        with patch('nexus_sandbox.recovery_guard.os.fsync', failing_sync):
            for _ in range(2):
                with self.assertRaises(OSError): self.worker.ensure(self.request)
                self.assert_no_transport()
        result = self.worker.ensure(self.request)
        self.assertEqual(result.protocol_verdict, 'VERIFIED')
        self.assertEqual(self.transport.writes, 1)

    def test_visible_pending_state_does_not_bypass_retry_commit(self):
        def uncertain_commit(path, data):
            atomic_inventory(path, data)
            raise OSError(errno.EIO, 'injected uncertainty after marker replacement')
        with patch('nexus_sandbox.recovery_guard.atomic_inventory', uncertain_commit):
            with self.assertRaises(OSError): self.worker.ensure(self.request)
        self.assert_no_transport()
        with patch('nexus_sandbox.recovery_guard.atomic_inventory', side_effect=OSError(errno.EIO, 'retry commit still unavailable')):
            with self.assertRaises(OSError): self.worker.ensure(self.request)
        self.assert_no_transport()
        self.assertEqual(json.loads(self.i.read_text())['state'], 'operation_pending')

    def test_file_sync_failure_preserves_ready_inventory_and_blocks_transport(self):
        before = self.i.read_bytes()
        with patch('nexus_sandbox.recovery_guard.os.fsync', side_effect=OSError(errno.EIO, 'file sync failed')):
            with self.assertRaises(OSError): self.worker.ensure(self.request)
        self.assert_no_transport()
        self.assertEqual(self.i.read_bytes(), before)
        self.assertEqual(list(self.i.parent.glob('*.pending-*')), [])

    def test_replacement_failure_preserves_ready_inventory_and_blocks_transport(self):
        before = self.i.read_bytes()
        with patch('nexus_sandbox.recovery_guard.os.replace', side_effect=OSError(errno.EIO, 'replace failed')):
            with self.assertRaises(OSError): self.worker.ensure(self.request)
        self.assert_no_transport()
        self.assertEqual(self.i.read_bytes(), before)
        self.assertEqual(list(self.i.parent.glob('*.pending-*')), [])

    def test_completion_directory_sync_failure_recovers_without_duplicate_write(self):
        sync = os.fsync
        def failing_completion(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode) and json.loads(self.i.read_text())['state'] == 'ready':
                raise OSError(errno.EIO, 'completion directory sync failed')
            return sync(fd)
        with patch('nexus_sandbox.recovery_guard.os.fsync', failing_completion):
            with self.assertRaises(OSError): self.worker.ensure(self.request)
        self.assertEqual(self.transport.writes, 1)
        self.assertEqual(self.worker.ensure(self.request).protocol_verdict, 'VERIFIED')
        self.assertEqual(self.transport.writes, 1)
