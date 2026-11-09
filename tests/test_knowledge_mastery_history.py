import unittest
from nexus_sandbox.knowledge_mastery_history import reconcile_history

def item(rid,rev,old=()):
    return dict(record_id=rid,revision=rev,supersedes=list(old),
                source_refs=["source:"+rid],evidence_refs=["evidence:"+rid],
                constitution_revision="constitution-2",
                review_independence_status="verified",contradiction_refs=[])

class HistoryTests(unittest.TestCase):
    def decide(self, records, constitution="constitution-2"):
        return reconcile_history(records=records,active_constitution_revision=constitution)
    def test_preserves_old_revision(self):
        d=self.decide([item("old",1),item("new",2,["old"])])
        self.assertEqual(d.status,"CANDIDATE_ONLY")
        self.assertEqual(d.effective_id,"new")
        self.assertEqual(d.preserved_ids,("new","old"))
        self.assertEqual(d.provider_writes,0)
        self.assertEqual(d.constitutional_changes,0)
    def test_stale_constitution_blocks(self):
        self.assertEqual(self.decide([item("old",1)],"constitution-3").reason,"STALE_CONSTITUTION")
    def test_unknown_supersession_blocks(self):
        self.assertEqual(self.decide([item("new",2,["missing"])]).reason,"INVALID_SUPERSESSION_TARGET")
    def test_conflicting_heads_require_review(self):
        self.assertEqual(self.decide([item("one",1),item("two",1)]).status,"REVIEW_REQUIRED")
    def test_nonmonotonic_revision_blocks(self):
        self.assertEqual(self.decide([item("old",2),item("new",1,["old"])]).reason,"NONMONOTONIC_REVISION")
    def test_unresolved_contradiction_blocks(self):
        r=item("old",1);r["contradiction_refs"]=["conflict"]
        self.assertEqual(self.decide([r]).reason,"UNRESOLVED_CONTRADICTION")
    def test_independent_review_required(self):
        r=item("old",1);r["review_independence_status"]="unavailable"
        self.assertEqual(self.decide([r]).reason,"INDEPENDENT_REVIEW_REQUIRED")
    def test_duplicate_ids_block(self):
        self.assertEqual(self.decide([item("same",1),item("same",2)]).reason,"DUPLICATE_OR_INVALID_ID")

if __name__=="__main__":
    unittest.main()
