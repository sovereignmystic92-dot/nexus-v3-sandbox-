import unittest
from nexus_sandbox.provider_evidence_envelope import inspect_envelope

class EnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.e={"transaction_id":"pilot:mara:1",
          "source":{"provider":"NOTION","record_id":"notion:40a8c067",
            "revision":"rev1","content_sha256":"a"*64,"complete":True,
            "truncated":False,"readback_kind":"FRESH_INDEPENDENT_FETCH"},
          "output":{"provider":"CORTEX","record_id":"cortex:module01",
            "revision":"v1","content_sha256":"b"*64,"complete":True,
            "truncated":False,"readback_kind":"FRESH_INDEPENDENT_FETCH"},
          "independent_readback":True,"authority_evidence":None}

    def test_valid_shape_is_never_authorized(self):
        v=inspect_envelope(self.e)
        self.assertEqual(v.status,"UNAUTHENTICATED_ENVELOPE_VALID")
        self.assertFalse(v.authenticated)
        self.assertFalse(v.write_authorized)
        self.assertEqual(v.cp09,"NOT_PROVEN")

    def test_wrong_destination(self):
        self.e["output"]["provider"]="NOTION"
        self.assertEqual(inspect_envelope(self.e).status,"HELD")

    def test_source_incomplete(self):
        self.e["source"]["complete"]=False
        self.assertIn("INCOMPLETE",inspect_envelope(self.e).next_action)

    def test_output_truncated(self):
        self.e["output"]["truncated"]=True
        self.assertIn("INCOMPLETE",inspect_envelope(self.e).next_action)

    def test_boolean_string_is_rejected(self):
        self.e["source"]["complete"]="true"
        self.assertIn("FLAGS",inspect_envelope(self.e).next_action)

    def test_missing_digest_rejected(self):
        self.e["output"]["content_sha256"]=""
        self.assertIn("DIGEST",inspect_envelope(self.e).next_action)

    def test_no_self_signed_claims(self):
        self.e["authority_evidence"]={"verified":True}
        self.assertEqual(inspect_envelope(self.e).next_action,"AUTHORITY_NOT_AUTHENTICATED")

    def test_untrusted_readback_flag(self):
        self.e["independent_readback"]="true"
        self.assertEqual(inspect_envelope(self.e).status,"HELD")

    def test_no_extra_fields(self):
        self.e["secret"]="never"
        self.assertEqual(inspect_envelope(self.e).status,"HELD")

    def test_revision_required(self):
        self.e["source"]["revision"]=""
        self.assertEqual(inspect_envelope(self.e).status,"HELD")

    def test_readback_kind(self):
        self.e["output"]["readback_kind"]="CHAT_MEMORY"
        self.assertEqual(inspect_envelope(self.e).status,"HELD")
