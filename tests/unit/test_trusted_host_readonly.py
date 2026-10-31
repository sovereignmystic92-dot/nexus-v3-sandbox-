import unittest
from hashlib import sha256
from nexus_sandbox.trusted_host_readonly import observe_existing

class MockClient:
    def __init__(self, id, raw, revision):
        self.item={"id":id,"revision":revision,"content_bytes":raw,
                   "complete":True,"truncated":False}
        self.perms={"edit":True,"owner":True}
        self.reads=0
    def read_exact(self, id):
        self.reads+=1
        return dict(self.item)
    def permissions_exact(self, id):
        return dict(self.perms)

class HostProbeTests(unittest.TestCase):
    def setUp(self):
        self.n=MockClient("notion:one",b"fictional transcript","r1")
        self.c=MockClient("cortex:one",b"fictional analysis","v2")
        self.i={"transaction_id":"pilot:one","notion_source_id":"notion:one",
                "notion_revision":"r1","notion_sha256":sha256(b"fictional transcript").hexdigest(),
                "cortex_output_id":"cortex:one","cortex_revision":"v2",
                "cortex_sha256":sha256(b"fictional analysis").hexdigest(),
                "policy_revision":"p1"}
    def check(self):
        return observe_existing(self.i,self.n,self.c)
    def test_match_is_read_only(self):
        x=self.check()
        self.assertEqual(x.status,"READ_ONLY_PROVIDER_SNAPSHOTS_MATCHED")
        self.assertEqual(x.provider_writes,0)
        self.assertFalse(x.write_authorized)
        self.assertEqual(x.cp09,"NOT_PROVEN")
        self.assertEqual(self.n.reads,1)
        self.assertEqual(self.c.reads,1)
    def test_wrong_source_bytes(self):
        self.n.item["content_bytes"]=b"other"
        self.assertEqual(self.check().status,"HELD")
    def test_wrong_output_bytes(self):
        self.c.item["content_bytes"]=b"other"
        self.assertEqual(self.check().status,"HELD")
    def test_stale_revision(self):
        self.n.item["revision"]="r2"
        self.assertEqual(self.check().status,"HELD")
    def test_stale_cortex(self):
        self.c.item["revision"]="v3"
        self.assertEqual(self.check().status,"HELD")
    def test_incomplete(self):
        self.n.item["complete"]=False
        self.assertEqual(self.check().status,"HELD")
    def test_truncation(self):
        self.c.item["truncated"]=True
        self.assertEqual(self.check().status,"HELD")
    def test_string_complete(self):
        self.n.item["complete"]="true"
        self.assertEqual(self.check().status,"HELD")
    def test_string_edit(self):
        self.c.perms["edit"]="true"
        self.assertEqual(self.check().status,"HELD")
    def test_no_edit(self):
        self.c.perms["edit"]=False
        self.assertEqual(self.check().status,"HELD")
    def test_no_owner(self):
        self.c.perms["owner"]=False
        self.assertEqual(self.check().status,"HELD")
    def test_exception(self):
        self.n.read_exact=lambda id: 1/0
        self.assertEqual(self.check().next_action,"PROVIDER_READ_OR_PERMISSION_ERROR")
    def test_missing_record_field(self):
        del self.c.item["content_bytes"]
        self.assertEqual(self.check().status,"HELD")
    def test_wrong_record_identity(self):
        self.n.item["id"]="notion:other"
        self.assertEqual(self.check().status,"HELD")
    def test_non_bytes(self):
        self.c.item["content_bytes"]="fictional analysis"
        self.assertEqual(self.check().status,"HELD")
