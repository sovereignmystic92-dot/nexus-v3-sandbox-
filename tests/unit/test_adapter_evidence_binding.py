import unittest
from nexus_sandbox.adapter_evidence_binding import assess_existing_records

class AdapterBindingTests(unittest.TestCase):
    def setUp(self):
        self.intent={"transaction_id":"mara:existing:one",
          "notion_source_id":"notion:source:1","notion_revision":"rev1",
          "notion_sha256":"a"*64,"cortex_output_id":"cortex:module:1",
          "cortex_revision":"v2","cortex_sha256":"b"*64,
          "policy_revision":"policy1"}
        self.observation={"transaction_id":"mara:existing:one",
          "source":{"provider":"NOTION","record_id":"notion:source:1",
                    "revision":"rev1","content_sha256":"a"*64,
                    "complete":True,"truncated":False,
                    "readback_kind":"FRESH_INDEPENDENT_FETCH"},
          "output":{"provider":"CORTEX","record_id":"cortex:module:1",
                    "revision":"v2","content_sha256":"b"*64,
                    "complete":True,"truncated":False,
                    "readback_kind":"FRESH_INDEPENDENT_FETCH"},
          "independent_readback":True,"authority_evidence":None}
    def check(self):
        return assess_existing_records(self.intent,self.observation)
    def test_match_does_not_authorize(self):
        result=self.check()
        self.assertEqual(result.status,"UNAUTHENTICATED_BINDING_MATCHED")
        self.assertFalse(result.authenticated)
        self.assertFalse(result.write_authorized)
        self.assertEqual(result.provider_writes,0)
        self.assertEqual(result.cp09,"NOT_PROVEN")
        self.assertEqual(len(result.intent_sha256),64)
    def test_wrong_transaction(self):
        self.observation["transaction_id"]="other"
        self.assertEqual(self.check().status,"HELD")
    def test_wrong_source(self):
        self.observation["source"]["record_id"]="notion:other"
        self.assertIn("NOTION",self.check().next_action)
    def test_wrong_output(self):
        self.observation["output"]["record_id"]="cortex:other"
        self.assertIn("CORTEX",self.check().next_action)
    def test_changed_source_revision(self):
        self.observation["source"]["revision"]="rev2"
        self.assertEqual(self.check().status,"HELD")
    def test_changed_output_version(self):
        self.observation["output"]["revision"]="v3"
        self.assertEqual(self.check().status,"HELD")
    def test_changed_source_content(self):
        self.observation["source"]["content_sha256"]="c"*64
        self.assertEqual(self.check().status,"HELD")
    def test_changed_output_content(self):
        self.observation["output"]["content_sha256"]="d"*64
        self.assertEqual(self.check().status,"HELD")
    def test_truncated_source(self):
        self.observation["source"]["truncated"]=True
        self.assertEqual(self.check().status,"HELD")
    def test_unverified_authority(self):
        self.observation["authority_evidence"]={"self_reported":True}
        self.assertEqual(self.check().status,"HELD")
    def test_invalid_intent(self):
        self.intent["notion_sha256"]="not-a-hash"
        self.assertEqual(self.check().status,"HELD")
