import unittest
from nexus_sandbox.chat_github_handshake import precheck,postcheck

class HandshakeTests(unittest.TestCase):
    def setUp(self):
        self.intent={"schema":"NEXUS_CHAT_GITHUB_HANDSHAKE_V1",
          "transaction_id":"synthetic:pilot:one","source_store":"NOTION",
          "source_id":"notion:source:one","source_revision":"r1",
          "source_sha256":"a"*64,"output_store":"CORTEX",
          "output_id":"cortex:output:one","output_revision":"v1",
          "intended_output_sha256":"b"*64,"policy_revision":"policy-v1",
          "mode":"SYNTHETIC_NO_WRITE"}
        self.receipt={"schema":"NEXUS_CHAT_GITHUB_RECEIPT_V1",
          "transaction_id":"synthetic:pilot:one",
          "intent_sha256":precheck(self.intent).intent_sha256,
          "source_sha256":"a"*64,"output_id":"cortex:output:one",
          "output_revision":"v1","observed_output_sha256":"b"*64,
          "complete_readback":True,"host_authority_verified":True}

    def test_precheck_never_grants_write(self):
        x=precheck(self.intent)
        self.assertEqual(x.status,"PRECHECK_VALIDATED")
        self.assertEqual(x.provider_writes,0)
        self.assertFalse(x.automatic_execution)
        self.assertEqual(x.cp09,"NOT_PROVEN")

    def test_postcheck_only_matches_synthetic(self):
        x=postcheck(self.intent,self.receipt)
        self.assertEqual(x.status,"SYNTHETIC_RECEIPT_MATCHED")
        self.assertEqual(x.provider_writes,0)

    def test_notional_output_rejected(self):
        self.assertEqual(precheck(dict(self.intent,output_store="NOTION")).status,"HELD")

    def test_live_mode_rejected(self):
        self.assertEqual(precheck(dict(self.intent,mode="LIVE")).status,"HELD")

    def test_bad_digest_rejected(self):
        self.assertEqual(precheck(dict(self.intent,source_sha256="x")).status,"HELD")

    def test_unknown_field_rejected(self):
        self.assertEqual(precheck(dict(self.intent,token="secret")).status,"HELD")

    def test_tampered_intent_rejected(self):
        modified=dict(self.intent,output_revision="v2")
        self.assertEqual(postcheck(modified,self.receipt).next_action,"RECONCILE_RECEIPT_BINDING")

    def test_mismatched_readback_held(self):
        x=postcheck(self.intent,dict(self.receipt,observed_output_sha256="c"*64))
        self.assertEqual(x.next_action,"OUTPUT_MISMATCH_NO_RETRY")

    def test_incomplete_readback_held(self):
        x=postcheck(self.intent,dict(self.receipt,complete_readback=False))
        self.assertEqual(x.next_action,"READBACK_INCOMPLETE_NO_RETRY")

    def test_missing_authority_held(self):
        x=postcheck(self.intent,dict(self.receipt,host_authority_verified=False))
        self.assertEqual(x.next_action,"HOST_AUTHORITY_UNVERIFIED")

    def test_untrusted_boolean_rejected(self):
        x=postcheck(self.intent,dict(self.receipt,complete_readback="true"))
        self.assertEqual(x.next_action,"INVALID_HOST_ASSERTIONS")

    def test_wrong_transaction_rejected(self):
        x=postcheck(self.intent,dict(self.receipt,transaction_id="synthetic:other"))
        self.assertEqual(x.next_action,"RECONCILE_RECEIPT_BINDING")

    def test_modified_output_id_held(self):
        x=postcheck(self.intent,dict(self.receipt,output_id="cortex:other"))
        self.assertEqual(x.next_action,"RECONCILE_RECEIPT_BINDING")
