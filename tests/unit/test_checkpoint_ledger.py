from copy import deepcopy
import unittest
from nexus_sandbox.checkpoint_ledger import validate,validate_transition,manifest_hash


def ledger(count):
    records=[]
    for seq in range(1,count+1):
        records.append({'workflow_version':'sandbox-recovery-v2','installation_id':'a'*32,
          'checkpoint_sequence':seq,'created_at_utc':'2026-10-24T22:00:00Z',
          'source_commit':'b'*40,'packet_sha256':str(seq)*64,
          'previous_manifest_sha256':manifest_hash(records[-1]) if records else None,
          'copies':{p:{'record_id':'synthetic:'+p+':'+str(seq),'packet_sha256':str(seq)*64} for p in ('notion','cortex')}})
    return {'schema_version':1,'records':records,'latest':None if not records else
            {'installation_id':'a'*32,'checkpoint_sequence':count,'manifest_sha256':manifest_hash(records[-1])}}


class CheckpointLedgerTests(unittest.TestCase):
    def test_empty_is_uninitialized_not_a_verified_checkpoint(self):
        self.assertIsNone(validate(ledger(0)))
    def test_valid_append_and_noop(self):
        self.assertEqual(validate_transition(ledger(1),ledger(2))['checkpoint_sequence'],2)
        self.assertEqual(validate_transition(ledger(2),ledger(2))['checkpoint_sequence'],2)
    def test_coherent_rollback_rejected_against_base(self):
        with self.assertRaises(ValueError):validate_transition(ledger(2),ledger(1))
    def test_coherent_rewrite_rejected_even_with_recomputed_hashes(self):
        changed=ledger(1);changed['records'][0]['created_at_utc']='2026-10-24T23:00:00Z'
        changed['latest']['manifest_sha256']=manifest_hash(changed['records'][0])
        self.assertIsNotNone(validate(changed))
        with self.assertRaises(ValueError):validate_transition(ledger(1),changed)
    def test_each_manifest_field_mismatch_holds(self):
        changes={'checkpoint_sequence':4,'installation_id':'bad','source_commit':'bad',
                 'packet_sha256':'bad','previous_manifest_sha256':'c'*64,
                 'workflow_version':'provider-version-3','created_at_utc':'tomorrow'}
        for field,value in changes.items():
            with self.subTest(field=field):
                altered=ledger(1);altered['records'][0][field]=value
                with self.assertRaises(ValueError):validate(altered)
    def test_missing_copy_or_mismatched_packet_holds(self):
        for mode in ('missing','mismatch'):
            altered=ledger(1)
            if mode=='missing':del altered['records'][0]['copies']['notion']
            else:altered['records'][0]['copies']['notion']['packet_sha256']='f'*64
            with self.assertRaises(ValueError):validate(altered)
    def test_latest_cannot_point_back_with_complete_history(self):
        altered=ledger(2);altered['latest']=ledger(1)['latest']
        with self.assertRaises(ValueError):validate(altered)
