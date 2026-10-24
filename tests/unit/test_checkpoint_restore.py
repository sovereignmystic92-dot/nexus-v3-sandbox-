import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zlib
from nexus_sandbox.checkpoint_gate import packet_digest
from nexus_sandbox.checkpoint_restore import restore_paired_checkpoint
from nexus_sandbox.recovery_guard import initialize,create_backup,RecoveryHold,check


class CheckpointRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);(root/'journal').mkdir();(root/'inventory').mkdir()
        self.j=root/'journal'/'journal.sqlite';self.i=root/'inventory'/'trusted.json'
        initialize(self.j,self.i)
        backup=root/'backup.sqlite';create_backup(self.j,self.i,backup)
        self.raw=backup.read_bytes();self.before=self.i.read_bytes()
        self.packet={'format':'nexus-paired-recovery-v1','synthetic':True,
                     'inventory':json.loads(self.before),'journal_encoding':'zlib+base64',
                     'journal_size_bytes':len(self.raw),'journal_sha256':hashlib.sha256(self.raw).hexdigest(),
                     'journal_data':base64.b64encode(zlib.compress(self.raw)).decode()}
        self.copies={p:deepcopy(self.packet) for p in ('cortex','notion')}
        self.witness={'installation_id':self.packet['inventory']['installation_id'],
                      'last_sequence':0,'packet_sha256':packet_digest(self.packet)}
        self.j.unlink()

    def restore(self):return restore_paired_checkpoint(self.j,self.i,self.copies,self.witness)
    def held(self):
        with self.assertRaises(RecoveryHold):self.restore()
        self.assertFalse(self.j.exists());self.assertEqual(self.i.read_bytes(),self.before)

    def bind_modified_packet(self):
        self.copies['notion']=deepcopy(self.copies['cortex'])
        self.witness['packet_sha256']=packet_digest(self.copies['cortex'])

    def test_exact_restore_retains_bytes_and_identity(self):
        result=self.restore()
        self.assertEqual(self.j.read_bytes(),self.raw)
        self.assertEqual(result['installation_id'],self.witness['installation_id'])
        self.assertEqual(self.i.read_bytes(),self.before);check(self.j,self.i)

    def test_conflict_does_not_touch_destination(self):
        self.copies['notion']['journal_sha256']='0'*64;self.held()

    def test_stale_copies_do_not_touch_destination(self):
        self.witness['last_sequence']=1;self.held()

    def test_missing_witness_does_not_touch_destination(self):
        self.witness=None;self.held()

    def test_retained_inventory_disagreement_holds(self):
        self.copies['cortex']['inventory']['anchors']={'unexpected':'identity'}
        self.bind_modified_packet();self.held()

    def test_bad_encoding_even_with_matching_packet_digest_holds(self):
        self.copies['cortex']['journal_data']='not base64!'
        self.bind_modified_packet();self.held()

    def test_trailing_compressed_data_holds(self):
        self.copies['cortex']['journal_data']=base64.b64encode(zlib.compress(self.raw)+b'trailing').decode()
        self.bind_modified_packet();self.held()

    def test_wrong_journal_digest_holds(self):
        self.copies['cortex']['journal_sha256']='0'*64
        self.bind_modified_packet();self.held()

    def test_existing_journal_is_preserved(self):
        self.j.write_bytes(b'existing evidence')
        with self.assertRaises(RecoveryHold):self.restore()
        self.assertEqual(self.j.read_bytes(),b'existing evidence')
        self.assertEqual(self.i.read_bytes(),self.before)

    def test_lost_inventory_is_not_bootstrapped(self):
        self.i.unlink()
        with self.assertRaises(RecoveryHold):self.restore()
        self.assertFalse(self.i.exists());self.assertFalse(self.j.exists())
