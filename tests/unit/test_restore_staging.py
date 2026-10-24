import os
import json
from copy import deepcopy
from pathlib import Path
import unittest
import test_checkpoint_restore as fixture
from nexus_sandbox.checkpoint_restore import cleanup_restore_staging,restore_paired_checkpoint
from nexus_sandbox.recovery_guard import RecoveryHold
from nexus_sandbox.checkpoint_gate import packet_digest


class RestoreStagingTests(unittest.TestCase):
    def setUp(self):
        fixture.CheckpointRestoreTests.setUp(self)
        self.root=self.j.parent.parent/'staging';self.root.mkdir(mode=0o700)
        self.folder=self.root/'nexus-checkpoint-aaaaaaaa';self.folder.mkdir(mode=0o700)
        self.staged=self.folder/'checkpoint.sqlite';self.staged.write_bytes(self.raw)

    def cleanup(self):
        return cleanup_restore_staging(self.j,self.i,self.copies,self.witness,self.root)

    def test_verified_cleanup_is_idempotent(self):
        self.assertEqual(self.cleanup(),[self.folder.name]);self.assertEqual(self.cleanup(),[])
        self.assertEqual(self.i.read_bytes(),self.before);self.assertFalse(self.j.exists())

    def test_next_restore_cleans_verified_old_staging(self):
        restore_paired_checkpoint(self.j,self.i,self.copies,self.witness,staging_root=self.root)
        self.assertEqual(list(self.root.iterdir()),[]);self.assertEqual(self.j.read_bytes(),self.raw)

    def test_mismatch_preserves_every_candidate(self):
        other=self.root/'nexus-checkpoint-bbbbbbbb';other.mkdir(mode=0o700)
        (other/'checkpoint.sqlite').write_bytes(b'unknown')
        with self.assertRaises(RecoveryHold):self.cleanup()
        self.assertTrue(self.staged.exists());self.assertTrue(other.exists())

    def test_symlink_preserves_all(self):
        other=self.root/'nexus-checkpoint-bbbbbbbb';other.symlink_to(self.folder)
        with self.assertRaises(RecoveryHold):self.cleanup()
        self.assertTrue(self.staged.exists());self.assertTrue(other.is_symlink())

    def test_hardlinked_backup_is_preserved(self):
        os.link(self.staged,self.j.parent/'retained-copy')
        with self.assertRaises(RecoveryHold):self.cleanup()
        self.assertTrue(self.staged.exists())

    def test_unknown_entry_holds(self):
        (self.root/'unrelated').write_text('preserve')
        with self.assertRaises(RecoveryHold):self.cleanup()
        self.assertTrue(self.staged.exists())

    def test_nonprivate_root_holds(self):
        self.root.chmod(0o755)
        with self.assertRaises(RecoveryHold):self.cleanup()
        self.assertTrue(self.staged.exists())

    def test_empty_interrupted_directory_can_be_cleaned(self):
        self.staged.unlink();self.assertEqual(self.cleanup(),[self.folder.name])

    def test_existing_journal_never_deleted_by_cleanup(self):
        self.j.write_bytes(b'preserve interrupted journal')
        self.cleanup();self.assertEqual(self.j.read_bytes(),b'preserve interrupted journal')

    def test_missing_witness_preserves_staging(self):
        self.witness=None
        with self.assertRaises(RecoveryHold):self.cleanup()
        self.assertTrue(self.staged.exists())

    def bind_journal_inside_staging(self):
        self.j=self.staged
        packet=self.copies['cortex']
        packet['inventory']['journal_path']=str(self.j)
        self.copies['notion']=deepcopy(packet)
        self.witness['packet_sha256']=packet_digest(packet)
        self.i.write_text(json.dumps(packet['inventory']))
        self.before=self.i.read_bytes()

    def test_exact_restored_journal_inside_staging_is_preserved(self):
        self.bind_journal_inside_staging()
        with self.assertRaisesRegex(RecoveryHold,'contains journal or inventory'):self.cleanup()
        self.assertEqual(self.j.read_bytes(),self.raw);self.assertEqual(self.i.read_bytes(),self.before)

    def test_symlink_ancestor_cannot_hide_contained_journal(self):
        self.bind_journal_inside_staging()
        alias=self.root.parent/'parent-alias';alias.symlink_to(self.root.parent,target_is_directory=True)
        self.root=alias/'staging'
        with self.assertRaisesRegex(RecoveryHold,'contains journal or inventory'):self.cleanup()
        self.assertEqual(self.j.read_bytes(),self.raw);self.assertEqual(self.i.read_bytes(),self.before)

    def test_root_containing_inventory_holds_before_scanning(self):
        self.root=self.i.parent;self.root.chmod(0o700)
        with self.assertRaisesRegex(RecoveryHold,'contains journal or inventory'):self.cleanup()
        self.assertEqual(self.i.read_bytes(),self.before);self.assertTrue(self.staged.exists())
