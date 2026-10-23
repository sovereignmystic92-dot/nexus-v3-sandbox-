"""Independent retained-record probes; named boundary cases document limitations."""
from dataclasses import asdict, replace
import json
from pathlib import Path
import sqlite3
import unittest
import test_cortex_adapter as fixtures
from nexus_sandbox.cortex_adapter import JournalIntegrityError, MARKER

class IndependentProbes(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.CortexAdapterTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def edit(self, sql, args=()):
        with sqlite3.connect(self.f.journal) as db:
            db.execute(sql,args)

    def hold(self,request=None):
        reads=len(self.f.transport.read_calls);writes=self.f.transport.writes
        with self.assertRaises(JournalIntegrityError):
            self.f.adapter().ensure(request or self.f.request)
        self.assertEqual((len(self.f.transport.read_calls),self.f.transport.writes),(reads,writes))

    def test_orphan_anchor_alone(self):
        self.f.adapter().ensure(self.f.request)
        self.edit('DELETE FROM cortex_receipts'); self.edit('DELETE FROM cortex_events')
        self.hold()

    def test_legacy_receipt_without_any_events_stops(self):
        self.f.adapter().ensure(self.f.request)
        self.edit('DROP TABLE cortex_identity_anchors');self.edit('DELETE FROM cortex_events')
        self.hold()

    def test_anchor_disagreement_stops(self):
        self.f.adapter().ensure(self.f.request)
        self.edit("UPDATE cortex_identity_anchors SET module_id='foreign-B'")
        self.hold()

    def test_update_history_loss_and_trusted_restore(self):
        self.f.adapter().ensure(self.f.request)
        before=self.f.transport.modules[fixtures.TARGET]
        key='synthetic:request:independent-update'
        request=replace(self.f.request,key=key,content=MARKER+key,before=before)
        self.f.adapter().ensure(request)
        with sqlite3.connect(self.f.journal) as db:
            events=db.execute('SELECT * FROM cortex_events WHERE key=?',(key,)).fetchall()
            db.execute('DELETE FROM cortex_events WHERE key=?',(key,))
        self.hold(request)
        with sqlite3.connect(self.f.journal) as db:
            db.executemany('INSERT INTO cortex_events VALUES(?,?,?,?)',events)
        self.assertEqual(self.f.adapter().ensure(request).protocol_verdict,'VERIFIED')
        self.assertEqual(self.f.transport.writes,2)

    def test_semantically_equivalent_latest_json_is_accepted(self):
        first=self.f.adapter().ensure(self.f.request)
        encoded=json.dumps(asdict(first),sort_keys=False,indent=4)
        self.edit('UPDATE cortex_receipts SET receipt=?',(encoded,))
        self.assertEqual(self.f.adapter().ensure(self.f.request).protocol_verdict,'VERIFIED')
        self.assertEqual(self.f.transport.writes,1)

    def test_pending_intent_has_no_anchor_and_reconciles_without_write(self):
        self.f.transport.crash=True
        with self.assertRaises(SystemExit):self.f.adapter().ensure(self.f.request)
        with sqlite3.connect(self.f.journal) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM cortex_identity_anchors').fetchone()[0],0)
        self.assertEqual(self.f.adapter().ensure(self.f.request).protocol_verdict,'VERIFIED')
        self.assertEqual(self.f.transport.writes,1)

    def test_event_failure_after_anchor_insert_rolls_back_all_verification_records(self):
        self.f.adapter()
        self.edit("CREATE TRIGGER deny_verified BEFORE INSERT ON cortex_events WHEN json_extract(NEW.receipt,'$.protocol_verdict')='VERIFIED' BEGIN SELECT RAISE(ABORT,'review fault'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.f.adapter().ensure(self.f.request)
        with sqlite3.connect(self.f.journal) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM cortex_identity_anchors').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM cortex_events').fetchone()[0],1)
            self.assertEqual(json.loads(db.execute('SELECT receipt FROM cortex_receipts').fetchone()[0])['checkpoint'],'WRITE_INTENT')
        self.edit('DROP TRIGGER deny_verified')
        self.assertEqual(self.f.adapter().ensure(self.f.request).protocol_verdict,'VERIFIED')
        self.assertEqual(self.f.transport.writes,1)

    def test_failed_legacy_migration_stops_before_transport_and_can_resume(self):
        self.f.adapter().ensure(self.f.request)
        self.edit('DELETE FROM cortex_identity_anchors')
        self.edit("CREATE TRIGGER deny_anchor BEFORE INSERT ON cortex_identity_anchors BEGIN SELECT RAISE(ABORT,'review fault'); END")
        reads=len(self.f.transport.read_calls)
        with self.assertRaises(sqlite3.IntegrityError):self.f.adapter().ensure(self.f.request)
        self.assertEqual(len(self.f.transport.read_calls),reads)
        with sqlite3.connect(self.f.journal) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM cortex_identity_anchors').fetchone()[0],0)
        self.edit('DROP TRIGGER deny_anchor')
        self.assertEqual(self.f.adapter().ensure(self.f.request).protocol_verdict,'VERIFIED')
        self.assertEqual(self.f.transport.writes,1)

    def test_malformed_json_tail_fails_before_transport(self):
        self.f.adapter().ensure(self.f.request)
        self.edit("INSERT INTO cortex_events(key,receipt,observed_at_utc) VALUES(?, '{', 'review')",(self.f.key,))
        reads=len(self.f.transport.read_calls)
        with self.assertRaises(json.JSONDecodeError):self.f.adapter().ensure(self.f.request)
        self.assertEqual(len(self.f.transport.read_calls),reads)

    def test_boundary_complete_database_loss_can_rebind_create(self):
        self.f.adapter().ensure(self.f.request)
        self.f.journal.unlink()
        self.f.transport.modules[fixtures.TARGET]=replace(self.f.transport.modules[fixtures.TARGET],id='foreign-B')
        result=self.f.adapter().ensure(self.f.request)
        self.assertEqual((result.protocol_verdict,result.module_id),('VERIFIED','foreign-B'))
        self.assertEqual(self.f.transport.writes,1)

    def test_boundary_preverified_observed_id_still_unpinned(self):
        create=self.f.transport.create
        def change_source(*args):
            create(*args)
            self.f.transport.modules[fixtures.SOURCE]=replace(self.f.source,version=99)
        self.f.transport.create=change_source
        first=self.f.adapter().ensure(self.f.request)
        self.assertEqual(first.checkpoint,'SOURCE_CHANGED');self.assertTrue(first.module_id)
        self.f.transport.modules[fixtures.SOURCE]=self.f.source
        self.f.transport.modules[fixtures.TARGET]=replace(self.f.transport.modules[fixtures.TARGET],id='foreign-B')
        result=self.f.adapter().ensure(self.f.request)
        self.assertEqual((result.protocol_verdict,result.module_id),('VERIFIED','foreign-B'))
        self.assertEqual(self.f.transport.writes,1)

    def test_boundary_nonobject_event_after_first_verification_is_not_validated(self):
        first=self.f.adapter().ensure(self.f.request)
        self.edit("INSERT INTO cortex_events(key,receipt,observed_at_utc) VALUES(?, '[]', 'review')",(self.f.key,))
        self.edit("INSERT INTO cortex_events(key,receipt,observed_at_utc) VALUES(?, ?, 'review')",(self.f.key,json.dumps(asdict(first))))
        reads=len(self.f.transport.read_calls)
        result=self.f.adapter().ensure(self.f.request)
        self.assertEqual((result.protocol_verdict,result.module_id),('VERIFIED',first.module_id))
        self.assertEqual(len(self.f.transport.read_calls)-reads,4)
        self.assertEqual(self.f.transport.writes,1)

class Results(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.cases=[]
    def record(self,test,status):
        self.cases.append({'test_id':test.id(),'status':status,'demonstrates_limitation':'test_boundary_' in test.id()})
    def addSuccess(self,test):
        super().addSuccess(test);self.record(test,'PASSED')
    def addFailure(self,test,error):
        super().addFailure(test,error);self.record(test,'FAILED')
    def addError(self,test,error):
        super().addError(test,error);self.record(test,'ERROR')
    def addSkip(self,test,reason):
        super().addSkip(test,reason);self.record(test,'SKIPPED')

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentProbes))
    Path(__file__).with_name('reviewer-probes-results.json').write_text(json.dumps({'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),'cases':result.cases},indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
