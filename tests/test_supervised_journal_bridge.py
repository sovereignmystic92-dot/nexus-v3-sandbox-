import hashlib
import unittest
from nexus_sandbox.transcript_ingestion import TranscriptCoordinator
from nexus_sandbox.supervised_journal_bridge import reconcile

class SupervisedJournalBridgeTests(unittest.TestCase):
    def setUp(self):
        self.db = TranscriptCoordinator(":memory:")
        self.addCleanup(self.db.close)
        self.video = "NykFQVLuSDA"
        raw = "test archive"
        sha = hashlib.sha256(raw.encode()).hexdigest()
        self.key = self.db.receive(self.video, raw)
        self.evidence = {"destination":"notion:page", "readback":"read-1",
                         "source_revision":"rev", "raw_sha256":sha}
        self.receipt = {"route":"supervised_connector",
            "source":{"page_id":"page","revision":"rev","sha256":sha,
                      "readback_sha256":sha,"bytes":len(raw),
                      "chunks":[{"index":0,"bytes":len(raw),"sha256":sha,"readback_sha256":sha}]},
            "claims":[{"p":0.01,"trials":150,"percent":77.85482127611391}],
            "output":{"module_id":"module","readback_module_id":"module",
                      "source_sha256":sha,"readback_source_sha256":sha,
                      "dependencies":["dep"],"readback_dependencies":["dep"]}}

    def archive(self):
        self.db.record(self.key,"NOTION_ARCHIVE_VERIFIED","COMPLETE",
                       self.evidence,independently_read_back=True)

    def test_missing_archive_holds(self):
        self.assertEqual(reconcile(self.db,self.video,self.receipt)["status"],
                         "FUNCTIONALLY_INCOMPLETE")

    def test_replay_is_read_only(self):
        self.archive()
        before = self.db.receipt(self.key)
        first = reconcile(self.db,self.video,self.receipt)
        self.assertEqual(first["status"],"RECEIPT_CONSISTENT")
        self.assertEqual(first["next_stage"],"ANALYSIS_COMPLETED")
        self.assertEqual(first["journal_status"],"INCOMPLETE")
        self.assertEqual(first["provider_writes"],0)
        self.assertEqual(first,reconcile(self.db,self.video,self.receipt))
        self.assertEqual(before,self.db.receipt(self.key))

    def test_conflicting_revision_holds(self):
        self.archive()
        self.receipt["source"]["revision"]="different"
        self.assertEqual(reconcile(self.db,self.video,self.receipt)["status"],
                         "FUNCTIONALLY_INCOMPLETE")

    def test_malformed_receipt_holds(self):
        self.archive()
        self.assertEqual(reconcile(self.db,self.video,None)["status"],
                         "FUNCTIONALLY_INCOMPLETE")
