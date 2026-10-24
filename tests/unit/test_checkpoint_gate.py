from copy import deepcopy
import unittest
from nexus_sandbox.checkpoint_gate import packet_digest, verify_checkpoint_copies
from nexus_sandbox.recovery_guard import RecoveryHold


class CheckpointGateTests(unittest.TestCase):
    def setUp(self):
        self.packet={'format':'nexus-paired-recovery-v1','synthetic':True,
                     'inventory':{'installation_id':'a'*32,'last_sequence':4,
                                  'state':'ready','pending_request':None},
                     'journal_sha256':'b'*64}
        self.copies={'cortex':deepcopy(self.packet),'notion':deepcopy(self.packet)}
        self.witness={'installation_id':'a'*32,'last_sequence':4,
                      'packet_sha256':packet_digest(self.packet)}

    def held(self):
        original=deepcopy(self.copies)
        with self.assertRaises(RecoveryHold):verify_checkpoint_copies(self.copies,self.witness)
        self.assertEqual(self.copies,original)

    def test_exact_copies_pass_detached(self):
        result=verify_checkpoint_copies(self.copies,self.witness)
        self.assertEqual(result,self.packet);self.assertIsNot(result,self.copies['cortex'])

    def test_missing_witness_holds(self):
        self.witness=None;self.held()

    def test_missing_copy_holds(self):
        del self.copies['notion'];self.held()

    def test_unexpected_provider_holds(self):
        self.copies['third']=deepcopy(self.packet);self.held()

    def test_one_stale_copy_holds(self):
        self.copies['notion']['inventory']['last_sequence']=3;self.held()

    def test_both_stale_hold(self):
        for p in self.copies.values():p['inventory']['last_sequence']=3
        self.held()

    def test_claimed_future_sequence_holds(self):
        for p in self.copies.values():p['inventory']['last_sequence']=5
        self.held()

    def test_equal_sequence_conflict_holds(self):
        self.copies['notion']['journal_sha256']='c'*64;self.held()

    def test_both_modified_hold(self):
        for p in self.copies.values():p['journal_sha256']='c'*64
        self.held()

    def test_foreign_identity_holds(self):
        self.copies['notion']['inventory']['installation_id']='d'*32;self.held()

    def test_pending_state_even_with_matching_digest_holds(self):
        for p in self.copies.values():p['inventory']['state']='operation_pending'
        self.witness['packet_sha256']=packet_digest(self.copies['cortex']);self.held()

    def test_boolean_sequence_holds(self):
        self.witness['last_sequence']=True;self.held()

    def test_malformed_packet_holds(self):
        self.copies['notion']=None;self.held()

    def test_coherent_rollback_with_rolled_back_witness_is_undetectable(self):
        # This is a demonstrated trust limitation, not a protection success.
        for p in self.copies.values():p['inventory']['last_sequence']=3
        self.witness['last_sequence']=3
        self.witness['packet_sha256']=packet_digest(self.copies['cortex'])
        self.assertEqual(verify_checkpoint_copies(self.copies,self.witness)['inventory']['last_sequence'],3)
