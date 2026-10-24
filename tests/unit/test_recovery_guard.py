from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from nexus_sandbox.cortex_adapter import Module,Write,MARKER
from nexus_sandbox.recovery_guard import (GuardedCortexAdapter,RecoveryHold,initialize,
                                         create_backup,restore_backup,check)
from nexus_sandbox.recovery_guard import atomic_inventory as actual_inventory_write

SOURCE='Nexus Sandbox Guard Source'
TARGET='Nexus Sandbox Guard Target'
ALLOW=frozenset((SOURCE,TARGET))


class Fake:
    def __init__(self,source):self.modules={SOURCE:source};self.reads=[];self.writes=0;self.lose_reply=False
    def get(self,name):self.reads.append(name);return self.modules.get(name)
    def create(self,name,content,dependencies):
        self.writes+=1
        self.modules[name]=Module('synthetic:target:original',name,1,content,dependencies)
        if self.lose_reply:raise TimeoutError('synthetic acknowledgment loss')
    def update(self,*args):raise AssertionError('No updates requested')


class RecoveryGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'journal').mkdir();(self.root/'inventory').mkdir()
        self.j=self.root/'journal'/'journal.sqlite';self.i=self.root/'inventory'/'trusted.json'
        source=Module('synthetic:source:guard',SOURCE,1,MARKER+'\nInvented source.',())
        self.transport=Fake(source);key='synthetic:request:guard'
        self.request=Write(key,TARGET,MARKER+'\n'+key+'\nInvented output.',(SOURCE,),source)

    def adapter(self):return GuardedCortexAdapter(self.j,self.i,ALLOW,self.transport)
    def seed(self):
        initialize(self.j,self.i)
        r=self.adapter().ensure(self.request)
        self.assertEqual(r.protocol_verdict,'VERIFIED')
        return r

    def fail_completion_update(self):
        calls=[]
        def write(path,data):
            calls.append(data['state'])
            if len(calls)==2:raise OSError('synthetic final inventory failure')
            return actual_inventory_write(path,data)
        return write

    def test_both_absent_do_not_initialize_implicitly(self):
        with self.assertRaises(RecoveryHold):self.adapter()
        self.assertFalse(self.j.exists());self.assertFalse(self.i.exists())

    def test_explicit_initialization_then_replay_retains_identity(self):
        first=self.seed();second=self.adapter().ensure(self.request)
        self.assertEqual(second.module_id,first.module_id);self.assertEqual(self.transport.writes,1)

    def test_missing_journal_stops_before_transport_and_never_recreates(self):
        self.seed();self.j.unlink();self.transport.reads.clear()
        with self.assertRaises(RecoveryHold):self.adapter()
        self.assertFalse(self.j.exists());self.assertEqual(self.transport.reads,[])
        self.assertEqual(self.transport.writes,1)

    def test_removal_after_startup_is_checked_on_ensure(self):
        self.seed();adapter=self.adapter();self.j.unlink();self.transport.reads.clear()
        with self.assertRaises(RecoveryHold):adapter.ensure(self.request)
        self.assertEqual(self.transport.reads,[]);self.assertFalse(self.j.exists())

    def test_inventory_missing_or_both_missing_hold(self):
        self.seed();self.i.unlink();self.transport.reads.clear()
        with self.assertRaises(RecoveryHold):self.adapter()
        self.j.unlink()
        with self.assertRaises(RecoveryHold):self.adapter()
        self.assertEqual(self.transport.reads,[])

    def test_reinitialization_refuses_existing_inventory_or_journal(self):
        self.seed();self.j.unlink()
        with self.assertRaises(RecoveryHold):initialize(self.j,self.i)
        self.assertFalse(self.j.exists())

    def test_interrupted_initialization_inventory_is_a_hold(self):
        initialize(self.j,self.i);d=json.loads(self.i.read_text());d['state']='initializing';self.i.write_text(json.dumps(d))
        with self.assertRaises(RecoveryHold):self.adapter()

    def test_damaged_journal_and_inventory_stop_before_transport(self):
        self.seed();self.j.write_bytes(b'bad database');self.transport.reads.clear()
        with self.assertRaises(sqlite3.DatabaseError):self.adapter()
        self.assertEqual(self.transport.reads,[])
        self.i.write_text('not JSON')
        with self.assertRaises(RecoveryHold):self.adapter()

    def test_valid_backup_restore_preserves_identity_no_duplicate(self):
        first=self.seed();backup=self.root/'backup.sqlite'
        create_backup(self.j,self.i,backup);self.j.unlink();restore_backup(self.j,self.i,backup)
        r=self.adapter().ensure(self.request)
        self.assertEqual(r.module_id,first.module_id);self.assertEqual(self.transport.writes,1)

    def test_changed_backup_bytes_refused_without_recreating_journal(self):
        self.seed();b=self.root/'backup.sqlite';create_backup(self.j,self.i,b)
        self.j.unlink();b.write_bytes(b.read_bytes()[:-100])
        with self.assertRaises(RecoveryHold):restore_backup(self.j,self.i,b)
        self.assertFalse(self.j.exists())

    def test_unregistered_backup_refused(self):
        self.seed();b=self.root/'unregistered.sqlite';b.write_bytes(self.j.read_bytes());self.j.unlink()
        with self.assertRaises(RecoveryHold):restore_backup(self.j,self.i,b)
        self.assertFalse(self.j.exists())

    def test_other_installation_backup_refused_even_if_added_to_catalog(self):
        self.seed();b=self.root/'other.sqlite';b.write_bytes(self.j.read_bytes())
        with sqlite3.connect(b) as db:db.execute('UPDATE recovery_installation SET installation_id=?',('f'*32,))
        d=json.loads(self.i.read_text());d['backups']=[{'sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'sequence':d['last_sequence']}];self.i.write_text(json.dumps(d))
        self.j.unlink()
        with self.assertRaises(RecoveryHold):restore_backup(self.j,self.i,b)
        self.assertFalse(self.j.exists())

    def test_stale_backup_rejected_against_newer_sequence_witness(self):
        self.seed();b=self.root/'old.sqlite';create_backup(self.j,self.i,b)
        self.adapter().ensure(self.request);self.j.unlink()
        with self.assertRaisesRegex(RecoveryHold,'predates'):restore_backup(self.j,self.i,b)
        self.assertFalse(self.j.exists())

    def test_mismatched_retained_anchor_stops_before_transport(self):
        self.seed()
        with sqlite3.connect(self.j) as db:db.execute('UPDATE cortex_identity_anchors SET module_id=?',('synthetic:replacement',))
        self.transport.reads.clear()
        with self.assertRaises(RecoveryHold):self.adapter()
        self.assertEqual(self.transport.reads,[])

    def test_backup_does_not_overwrite_damaged_journal_evidence(self):
        self.seed();b=self.root/'backup.sqlite';create_backup(self.j,self.i,b)
        self.j.write_bytes(b'preserve this damaged evidence')
        with self.assertRaises(RecoveryHold):restore_backup(self.j,self.i,b)
        self.assertEqual(self.j.read_bytes(),b'preserve this damaged evidence')

    def test_restore_then_remote_replacement_does_not_verify(self):
        self.seed();b=self.root/'backup.sqlite';create_backup(self.j,self.i,b);self.j.unlink()
        self.transport.modules[TARGET]=replace(self.transport.modules[TARGET],id='synthetic:replacement')
        restore_backup(self.j,self.i,b);result=self.adapter().ensure(self.request)
        self.assertNotEqual(result.protocol_verdict,'VERIFIED');self.assertEqual(self.transport.writes,1)

    def test_lost_reply_can_reconcile_with_guard_without_second_write(self):
        initialize(self.j,self.i);self.transport.lose_reply=True
        self.assertEqual(self.adapter().ensure(self.request).protocol_verdict,'UNKNOWN')
        self.assertEqual(self.adapter().ensure(self.request).protocol_verdict,'VERIFIED')
        self.assertEqual(self.transport.writes,1)

    def test_same_directory_and_symlink_inventory_are_refused(self):
        with self.assertRaises(RecoveryHold):initialize(self.j,self.j.with_name('sidecar.json'))
        self.seed();link=self.root/'inventory'/'link.json';link.symlink_to(self.i)
        with self.assertRaises(RecoveryHold):check(self.j,link)

    def test_wrong_expected_journal_path_refused(self):
        self.seed()
        with self.assertRaises(RecoveryHold):check(self.root/'journal'/'other.sqlite',self.i)

    def test_backup_catalog_does_not_hold_secrets_or_claim_authentication(self):
        self.seed();b=self.root/'backup.sqlite';entry=create_backup(self.j,self.i,b)
        self.assertEqual(set(entry),{'sha256','sequence'})
        self.assertEqual(entry['sha256'],hashlib.sha256(b.read_bytes()).hexdigest())

    def test_inventory_update_failure_recovers_with_existing_journal(self):
        initialize(self.j,self.i);adapter=self.adapter()
        with patch('nexus_sandbox.recovery_guard.atomic_inventory',side_effect=self.fail_completion_update()):
            with self.assertRaises(OSError):adapter.ensure(self.request)
        self.assertEqual(self.transport.writes,1)
        result=self.adapter().ensure(self.request)
        self.assertEqual(result.protocol_verdict,'VERIFIED');self.assertEqual(self.transport.writes,1)

    def test_pending_marker_refuses_old_backup_after_final_inventory_failure(self):
        initialize(self.j,self.i);b=self.root/'prewrite.sqlite';create_backup(self.j,self.i,b)
        adapter=self.adapter()
        with patch('nexus_sandbox.recovery_guard.atomic_inventory',side_effect=self.fail_completion_update()):
            with self.assertRaises(OSError):adapter.ensure(self.request)
        self.j.unlink()
        self.transport.modules[TARGET]=replace(self.transport.modules[TARGET],id='synthetic:replacement-after-split-commit')
        self.transport.reads.clear()
        with self.assertRaisesRegex(RecoveryHold,'pending'):restore_backup(self.j,self.i,b)
        with self.assertRaises(RecoveryHold):self.adapter()
        self.assertFalse(self.j.exists());self.assertEqual(self.transport.reads,[])
        self.assertEqual(self.transport.writes,1)

    def test_pending_marker_failure_prevents_transport_effects(self):
        initialize(self.j,self.i);adapter=self.adapter()
        with patch('nexus_sandbox.recovery_guard.atomic_inventory',side_effect=OSError('synthetic pending marker failure')):
            with self.assertRaises(OSError):adapter.ensure(self.request)
        self.assertEqual(self.transport.reads,[]);self.assertEqual(self.transport.writes,0)

    def test_pending_request_must_be_reconciled_before_a_different_request(self):
        initialize(self.j,self.i);adapter=self.adapter()
        with patch('nexus_sandbox.recovery_guard.atomic_inventory',side_effect=self.fail_completion_update()):
            with self.assertRaises(OSError):adapter.ensure(self.request)
        self.transport.reads.clear()
        key='synthetic:request:different'
        changed=replace(self.request,key=key,content=MARKER+'\n'+key)
        with self.assertRaisesRegex(RecoveryHold,'pending'):self.adapter().ensure(changed)
        self.assertEqual(self.transport.reads,[]);self.assertEqual(self.transport.writes,1)

    def test_pending_operation_cannot_register_a_new_backup(self):
        initialize(self.j,self.i);adapter=self.adapter()
        with patch('nexus_sandbox.recovery_guard.atomic_inventory',side_effect=self.fail_completion_update()):
            with self.assertRaises(OSError):adapter.ensure(self.request)
        b=self.root/'pending.sqlite'
        with self.assertRaisesRegex(RecoveryHold,'pending'):create_backup(self.j,self.i,b)
        self.assertFalse(b.exists())
