import json
import os
from pathlib import Path
import selectors
import sqlite3
import subprocess
import sys
import unittest

import test_checkpoint_restore as fixture_module
from nexus_sandbox.checkpoint_restore import cleanup_restore_staging, restore_paired_checkpoint


class ProcessReadbackTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture_module.CheckpointRestoreTests('test_exact_restore_retains_bytes_and_identity')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture
        self.env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[2] / 'src'))

    def fresh_check(self):
        return subprocess.run([sys.executable, '-B', '-c',
            'import json,sys;from nexus_sandbox.recovery_guard import check;'
            'print(json.dumps(check(sys.argv[1],sys.argv[2]),sort_keys=True))',
            str(self.f.j), str(self.f.i)], env=self.env, capture_output=True, text=True, timeout=10)

    def test_fresh_process_reads_restored_identity_and_inventory(self):
        self.f.restore()
        result=self.fresh_check()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),json.loads(self.f.before))
        self.assertEqual(self.f.j.read_bytes(),self.f.raw)

    def test_fresh_process_rejects_changed_restored_identity_without_repair(self):
        self.f.restore()
        with sqlite3.connect(self.f.j) as db:
            db.execute("UPDATE recovery_installation SET installation_id=?",('0'*32,))
        damaged=self.f.j.read_bytes()
        result=self.fresh_check()
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.f.j.read_bytes(),damaged)
        self.assertEqual(self.f.i.read_bytes(),self.f.before)

    def test_killed_restore_staging_is_cleaned_then_recovered_and_freshly_read(self):
        root=self.f.j.parent.parent
        staging=root/'private-staging';staging.mkdir(mode=0o700)
        packet=root/'packet.json'
        packet.write_text(json.dumps({'copies':self.f.copies,'witness':self.f.witness}))
        code='''import json,sys
import nexus_sandbox.checkpoint_restore as restore
data=json.load(open(sys.argv[3]))
def stop_before_publication(*args):
    print('STAGED',flush=True)
    sys.stdin.read(1)
    raise RuntimeError('unexpected resume')
restore.restore_backup=stop_before_publication
restore.restore_paired_checkpoint(sys.argv[1],sys.argv[2],data['copies'],data['witness'],staging_root=sys.argv[4])
'''
        proc=subprocess.Popen([sys.executable,'-B','-c',code,str(self.f.j),str(self.f.i),str(packet),str(staging)],
                              env=self.env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            with selectors.DefaultSelector() as ready:
                ready.register(proc.stdout,selectors.EVENT_READ)
                self.assertTrue(ready.select(10),'child did not reach staging barrier')
                self.assertEqual(proc.stdout.readline().strip(),'STAGED')
            proc.kill();proc.wait(timeout=10)
        finally:
            if proc.poll() is None:proc.kill()
            proc.communicate(timeout=10)
        self.assertFalse(self.f.j.exists())
        self.assertEqual(self.f.i.read_bytes(),self.f.before)
        self.assertEqual(len(list(staging.glob('nexus-checkpoint-*'))),1)
        removed=cleanup_restore_staging(self.f.j,self.f.i,self.f.copies,self.f.witness,staging)
        self.assertEqual(len(removed),1)
        self.assertEqual(list(staging.iterdir()),[])
        restore_paired_checkpoint(self.f.j,self.f.i,self.f.copies,self.f.witness,staging_root=staging)
        self.assertEqual(self.fresh_check().returncode,0)
        self.assertEqual(list(staging.iterdir()),[])
