from copy import deepcopy
import unittest
from nexus_sandbox.checkpoint_ledger import manifest_hash
from nexus_sandbox.public_checkpoint import validate_public,validate_public_transition,bind_private_checkpoint
from nexus_sandbox.checkpoint_gate import packet_digest


def public(digest='a'*64,count=1):
    entries=[]
    for seq in range(1,count+1):
        entries.append({'checkpoint_sequence':seq,'created_at_utc':'2026-10-24T23:00:00Z',
                        'source_commit':'b'*40,'private_manifest_sha256':digest,
                        'previous_entry_sha256':manifest_hash(entries[-1]) if entries else None})
    return {'schema_version':2,'records':entries,'latest':None if not entries else
            {'checkpoint_sequence':count,'entry_sha256':manifest_hash(entries[-1]),'private_manifest_sha256':digest}}


class PublicCheckpointTests(unittest.TestCase):
    def test_migrate_only_uninitialized_old_ledger(self):
        self.assertIsNotNone(validate_public_transition({'schema_version':1,'records':[],'latest':None},public()))
        with self.assertRaises(ValueError):validate_public_transition({'schema_version':1,'records':[{}],'latest':None},public())
    def test_append_and_noop(self):
        self.assertEqual(validate_public_transition(public(),public(count=2))['checkpoint_sequence'],2)
        self.assertEqual(validate_public_transition(public(),public())['checkpoint_sequence'],1)
    def test_coherent_rollback_and_rewrite_are_rejected(self):
        with self.assertRaises(ValueError):validate_public_transition(public(count=2),public())
        with self.assertRaises(ValueError):validate_public_transition(public(),public('c'*64))
    def test_private_metadata_fields_refused(self):
        for key in ('installation_id','copies','notion_page_id','cortex_module_id','packet','journal_data'):
            x=public();x['records'][0][key]='forbidden'
            with self.subTest(key=key),self.assertRaises(ValueError):validate_public(x)
    def test_latest_and_chain_mismatch_rejected(self):
        for mode in ('latest','chain'):
            x=public(count=2)
            if mode=='latest':x['latest']=public()['latest']
            else:x['records'][1]['previous_entry_sha256']='f'*64
            with self.assertRaises(ValueError):validate_public(x)
    def test_private_binding_and_stale_manifest_rejection(self):
        packet={'format':'nexus-paired-recovery-v1','synthetic':True,'inventory':{
                'installation_id':'d'*32,'last_sequence':7,'state':'ready','pending_request':None}}
        digest=packet_digest(packet)
        manifest={'checkpoint_sequence':1,'installation_id':'d'*32,'packet_sha256':digest,
                  'copies':{p:{'record_id':'synthetic:'+p,'packet_sha256':digest} for p in ('notion','cortex')}}
        copies={p:deepcopy(packet) for p in ('notion','cortex')}
        ids={p:'synthetic:'+p for p in copies};ledger=public(manifest_hash(manifest))
        self.assertEqual(bind_private_checkpoint(ledger,manifest,copies,ids)[0],packet)
        stale=deepcopy(manifest);stale['checkpoint_sequence']=0
        with self.assertRaises(ValueError):bind_private_checkpoint(ledger,stale,copies,ids)
        ids['notion']='foreign'
        with self.assertRaises(ValueError):bind_private_checkpoint(ledger,manifest,copies,ids)
    def test_coherently_changed_packets_still_rejected(self):
        packet={'format':'nexus-paired-recovery-v1','synthetic':True,'inventory':{
                'installation_id':'d'*32,'last_sequence':7,'state':'ready','pending_request':None}}
        digest=packet_digest(packet);ids={p:'synthetic:'+p for p in ('notion','cortex')}
        manifest={'checkpoint_sequence':1,'installation_id':'d'*32,'packet_sha256':digest,
                  'copies':{p:{'record_id':ids[p],'packet_sha256':digest} for p in ids}}
        copies={p:deepcopy(packet) for p in ids}
        for x in copies.values():x['inventory']['last_sequence']=6
        with self.assertRaises(ValueError):bind_private_checkpoint(public(manifest_hash(manifest)),manifest,copies,ids)
