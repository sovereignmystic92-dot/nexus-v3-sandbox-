import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

from nexus_sandbox.checkpoint_gate import packet_digest
from nexus_sandbox.loss_recovery import restore_lost_local_state
from nexus_sandbox.recovery_guard import initialize, create_backup, check, RecoveryHold
from nexus_sandbox.recovery_guard import GuardedCortexAdapter
from nexus_sandbox.cortex_adapter import Module, Write, MARKER
from test_cortex_adapter import FakeCortex, SOURCE, TARGET, NAMES


class TotalLocalStateLossTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / 'local/journal').mkdir(parents=True)
        (self.root / 'local/inventory').mkdir()
        self.j = self.root / 'local/journal/state.sqlite'
        self.i = self.root / 'local/inventory/trusted.json'
        initialize(self.j, self.i)
        self.source=Module('synthetic:module:loss-source',SOURCE,1,MARKER+' loss source',())
        self.transport=FakeCortex(self.source)
        self.request=Write('synthetic:request:loss-recovery',TARGET,
                           MARKER+' synthetic:request:loss-recovery',(SOURCE,),self.source)
        observed=GuardedCortexAdapter(self.j,self.i,NAMES,self.transport).ensure(self.request)
        self.assertEqual(observed.protocol_verdict,'VERIFIED')
        self.remote_id=observed.module_id
        backup = self.root / 'external-backup.sqlite'
        create_backup(self.j, self.i, backup)
        self.raw = backup.read_bytes()
        self.data = json.loads(self.i.read_text())
        self.packet = {'format':'nexus-paired-recovery-v1', 'synthetic':True,
                       'inventory':self.data, 'journal_encoding':'zlib+base64',
                       'journal_size_bytes':len(self.raw),
                       'journal_sha256':hashlib.sha256(self.raw).hexdigest(),
                       'journal_data':base64.b64encode(zlib.compress(self.raw)).decode()}
        self.copies = {name:deepcopy(self.packet) for name in ('cortex','notion')}
        self.latest = {'installation_id':self.data['installation_id'], 'last_sequence':self.data['last_sequence'],
                       'packet_sha256':packet_digest(self.packet)}
        # Actual deletion of the entire declared local directory, not just DB.
        shutil.rmtree(self.root / 'local')
        backup.unlink()
        (self.root / 'local/journal').mkdir(parents=True)
        (self.root / 'local/inventory').mkdir()

    def restore(self):
        return restore_lost_local_state(self.j,self.i,self.copies,self.latest)

    def assert_held(self):
        with self.assertRaises(RecoveryHold):
            self.restore()
        self.assertFalse(self.j.exists())
        self.assertFalse(self.i.exists())

    def test_complete_local_directory_loss_restores_exact_bytes_and_inventory(self):
        result = self.restore()
        self.assertEqual(self.j.read_bytes(),self.raw)
        self.assertEqual(json.loads(self.i.read_text()),self.data)
        self.assertEqual(result,check(self.j,self.i))

    def test_coherently_rewritten_copies_cannot_override_external_witness(self):
        for copy in self.copies.values():
            copy['inventory']['installation_id'] = 'f'*32
        self.assert_held()

    def test_coherently_stale_copies_rejected_by_current_external_digest(self):
        for copy in self.copies.values():
            copy['historical_marker'] = 'older-checkpoint'
        self.assert_held()

    def test_missing_external_witness_holds_without_bootstrap(self):
        self.latest = None
        self.assert_held()

    def test_corrupt_backup_rejected_even_with_matching_outer_digest(self):
        for copy in self.copies.values():
            raw = b'not a sqlite database'
            copy.update(journal_size_bytes=len(raw),journal_sha256=hashlib.sha256(raw).hexdigest(),
                        journal_data=base64.b64encode(zlib.compress(raw)).decode())
            copy['inventory']['backups']=[{'sha256':copy['journal_sha256'],'sequence':self.data['last_sequence']}]
        self.latest['packet_sha256']=packet_digest(self.copies['cortex'])
        self.assert_held()

    def test_wrong_path_rejected_before_inventory_publication(self):
        for copy in self.copies.values():
            copy['inventory']['journal_path'] = '/wrong/synthetic/path.sqlite'
        self.latest['packet_sha256']=packet_digest(self.copies['cortex'])
        self.assert_held()

    def test_interrupted_after_inventory_publication_can_resume_exact_packet(self):
        with patch('nexus_sandbox.loss_recovery.restore_backup',side_effect=OSError('synthetic interruption')):
            with self.assertRaises(OSError):
                self.restore()
        self.assertTrue(self.i.exists())
        self.assertFalse(self.j.exists())
        self.assertEqual(self.restore(),check(self.j,self.i))

    def test_conflicting_retained_inventory_preserved(self):
        changed = deepcopy(self.data)
        changed['installation_id']='e'*32
        self.i.write_text(json.dumps(changed))
        before=self.i.read_bytes()
        with self.assertRaises(RecoveryHold):
            self.restore()
        self.assertEqual(self.i.read_bytes(),before)
        self.assertFalse(self.j.exists())

    def test_existing_journal_preserved_without_duplicate_bootstrap(self):
        self.restore()
        before=(self.j.read_bytes(),self.i.read_bytes())
        with self.assertRaises(RecoveryHold):
            self.restore()
        self.assertEqual((self.j.read_bytes(),self.i.read_bytes()),before)

    def test_fresh_process_reconciles_recovered_committed_request_without_remote_write(self):
        from dataclasses import asdict
        self.restore()
        payload={'request':asdict(self.request),
                 'modules':{name:asdict(value) for name,value in self.transport.modules.items()}}
        script='''
import json,sys
from nexus_sandbox.cortex_adapter import Module,Write
from nexus_sandbox.recovery_guard import GuardedCortexAdapter
d=json.loads(sys.argv[3])
def module(v):return Module(v['id'],v['name'],v['version'],v['content'],tuple(v['dependencies']))
class Reader:
    def get(self,name):return module(d['modules'][name]) if name in d['modules'] else None
    def create(self,*args):raise AssertionError('Duplicate remote write forbidden')
    def update(self,*args):raise AssertionError('Remote update forbidden')
r=d['request'];request=Write(r['key'],r['name'],r['content'],tuple(r['dependencies']),module(r['source']))
a=GuardedCortexAdapter(sys.argv[1],sys.argv[2],frozenset(d['modules']),Reader())
out=a.ensure(request)
print(json.dumps({'operation':out.operation_outcome,'verdict':out.protocol_verdict,'id':out.module_id}))
'''
        env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]/'src'))
        proc=subprocess.run([sys.executable,'-c',script,str(self.j),str(self.i),json.dumps(payload)],
                            text=True,capture_output=True,check=True,timeout=15,env=env)
        self.assertEqual(json.loads(proc.stdout),
                         {'operation':'NOT_ATTEMPTED','verdict':'VERIFIED','id':self.remote_id})
