import os
from pathlib import Path
import tempfile
import unittest
from nexus_sandbox.recovery_guard import initialize, cleanup_staged_inventory, RecoveryHold


class StagedCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        (root/'journal').mkdir();(root/'inventory').mkdir()
        self.j=root/'journal'/'journal.sqlite';self.i=root/'inventory'/'trusted.json'
        initialize(self.j,self.i)
        self.stage=self.i.with_name(self.i.name+'.pending-'+'a'*32)
        self.stage.write_text('uncommitted data, never adopted')

    def test_removes_only_staging_and_is_idempotent(self):
        old_i=self.i.read_bytes();old_j=self.j.read_bytes()
        other=self.i.parent/'unrelated';other.write_text('retain')
        self.assertEqual(cleanup_staged_inventory(self.j,self.i),[self.stage.name])
        self.assertEqual(cleanup_staged_inventory(self.j,self.i),[])
        self.assertEqual(self.i.read_bytes(),old_i);self.assertEqual(self.j.read_bytes(),old_j)
        self.assertTrue(other.exists())

    def test_missing_journal_preserves_staging(self):
        self.j.unlink()
        with self.assertRaises(RecoveryHold):cleanup_staged_inventory(self.j,self.i)
        self.assertTrue(self.stage.exists());self.assertFalse(self.j.exists())

    def test_symlink_preflight_preserves_all_candidates(self):
        bad=self.i.with_name(self.i.name+'.pending-'+'b'*32);bad.symlink_to(self.i)
        with self.assertRaises(RecoveryHold):cleanup_staged_inventory(self.j,self.i)
        self.assertTrue(self.stage.exists());self.assertTrue(bad.is_symlink())

    def test_hardlink_preflight_preserves_all_candidates(self):
        bad=self.i.with_name(self.i.name+'.pending-'+'b'*32);os.link(self.i,bad)
        with self.assertRaises(RecoveryHold):cleanup_staged_inventory(self.j,self.i)
        self.assertTrue(self.stage.exists());self.assertTrue(bad.exists())

    def test_unexpected_name_preserved(self):
        bad=self.i.with_name(self.i.name+'.pending-unknown');bad.write_text('preserve')
        with self.assertRaises(RecoveryHold):cleanup_staged_inventory(self.j,self.i)
        self.assertTrue(self.stage.exists());self.assertTrue(bad.exists())
