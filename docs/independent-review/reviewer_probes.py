"""Independent adversarial probes; passing boundary cases document limitations."""
from dataclasses import replace
import json
import sqlite3
import unittest
import test_cortex_adapter as fixtures
from test_cortex_adapter import TARGET, SOURCE, MARKER

class IndependentProbes(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.CortexAdapterTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f = self.fixture

    def event_edit(self, sql, args=()):
        with sqlite3.connect(self.f.journal) as db:
            db.execute(sql, args)

    def test_many_replacements_and_source_outage_cannot_repin_verified_create(self):
        original = self.f.adapter().ensure(self.f.request)
        module = self.f.transport.modules[TARGET]
        for index in range(12):
            self.f.transport.modules[TARGET] = replace(module, id='foreign-'+str(index))
            self.f.transport.read_fail = index % 3 == 0
            self.assertNotEqual(self.f.adapter().ensure(self.f.request).protocol_verdict, 'VERIFIED')
        self.f.transport.read_fail = False
        self.f.transport.modules[TARGET] = module
        final = self.f.adapter().ensure(self.f.request)
        self.assertEqual((final.protocol_verdict, final.module_id), ('VERIFIED',original.module_id))
        self.assertEqual(self.f.transport.writes, 1)

    def test_corrupt_event_json_fails_before_transport(self):
        self.f.adapter().ensure(self.f.request)
        self.event_edit("UPDATE cortex_events SET receipt='{' WHERE sequence=1")
        reads = len(self.f.transport.read_calls)
        with self.assertRaises(json.JSONDecodeError):
            self.f.adapter().ensure(self.f.request)
        self.assertEqual(len(self.f.transport.read_calls), reads)
        self.assertEqual(self.f.transport.writes, 1)

    def test_verified_event_missing_id_fails_before_transport(self):
        self.f.adapter().ensure(self.f.request)
        self.event_edit('UPDATE cortex_events SET receipt=? WHERE sequence=(SELECT max(sequence) FROM cortex_events)',
                        (json.dumps({'protocol_verdict':'VERIFIED'}),))
        reads = len(self.f.transport.read_calls)
        with self.assertRaises(ValueError):
            self.f.adapter().ensure(self.f.request)
        self.assertEqual(len(self.f.transport.read_calls), reads)

    def test_history_loss_can_rebind_create_even_when_latest_receipt_retains_A(self):
        self.f.adapter().ensure(self.f.request)
        self.event_edit('DELETE FROM cortex_events')
        self.f.transport.modules[TARGET] = replace(self.f.transport.modules[TARGET], id='replacement-B')
        result = self.f.adapter().ensure(self.f.request)
        self.assertEqual((result.protocol_verdict,result.module_id), ('VERIFIED','replacement-B'))
        self.assertEqual(self.f.transport.writes,1)

    def test_preverification_observed_identity_is_not_pinned(self):
        create = self.f.transport.create
        def create_then_block_source(*args):
            create(*args)
            self.f.transport.modules[SOURCE] = replace(self.f.source,version=999)
        self.f.transport.create = create_then_block_source
        first = self.f.adapter().ensure(self.f.request)
        self.assertEqual(first.checkpoint,'SOURCE_CHANGED')
        observed_A = first.module_id
        self.assertTrue(observed_A)
        self.f.transport.modules[SOURCE] = self.f.source
        self.f.transport.modules[TARGET] = replace(self.f.transport.modules[TARGET],id='replacement-B')
        final = self.f.adapter().ensure(self.f.request)
        self.assertEqual((final.protocol_verdict,final.module_id), ('VERIFIED','replacement-B'))
        self.assertNotEqual(observed_A, final.module_id)
        self.assertEqual(self.f.transport.writes,1)

    def test_update_uncertainty_and_history_loss_still_require_before_id(self):
        self.f.adapter().ensure(self.f.request)
        before = self.f.transport.modules[TARGET]
        key='synthetic:request:independent-update'
        request=replace(self.f.request,key=key,content=MARKER+key,before=before)
        self.f.transport.lose_reply=True
        self.assertEqual(self.f.adapter().ensure(request).protocol_verdict,'UNKNOWN')
        self.event_edit('DELETE FROM cortex_events WHERE key=?',(key,))
        updated = self.f.transport.modules[TARGET]
        self.f.transport.modules[TARGET] = replace(updated,id='foreign-B')
        for _ in range(3):
            self.assertNotEqual(self.f.adapter().ensure(request).protocol_verdict,'VERIFIED')
        self.f.transport.modules[TARGET]=updated
        self.assertEqual(self.f.adapter().ensure(request).protocol_verdict,'VERIFIED')
        self.assertEqual(self.f.transport.writes,2)

    def test_postwrite_verified_journal_failure_never_returns_verified(self):
        self.f.adapter()
        self.event_edit("CREATE TRIGGER deny_verified BEFORE INSERT ON cortex_events WHEN json_extract(NEW.receipt,'$.protocol_verdict')='VERIFIED' BEGIN SELECT RAISE(ABORT,'review failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.f.adapter().ensure(self.f.request)
        with sqlite3.connect(self.f.journal) as db:
            row=db.execute('SELECT intent_sent,receipt FROM cortex_receipts').fetchone()
            self.assertEqual((row[0],json.loads(row[1])['checkpoint']),(1,'WRITE_INTENT'))
        self.event_edit('DROP TRIGGER deny_verified')
        self.assertEqual(self.f.adapter().ensure(self.f.request).protocol_verdict,'VERIFIED')
        self.assertEqual(self.f.transport.writes,1)

if __name__=='__main__':
    unittest.main(verbosity=2)
