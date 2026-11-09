import unittest
from nexus_sandbox.knowledge_mastery_exchange import prepare_exchange

def candidate():
    return dict(subject_id="subject", source_refs=["source1"], evidence_refs=["proof1"],
                evaluation_ids=["eval1"], constitution_revision="rev2",
                contradiction_refs=[], mastery_level=3)

class MasteryExchangeTests(unittest.TestCase):
    def decide(self, item=None, recipients=("research", "planning"), revision="rev2"):
        return prepare_exchange(candidate=candidate() if item is None else item,
                                recipient_modules=recipients,
                                active_constitution_revision=revision)
    def test_valid_candidate_never_writes(self):
        d=self.decide()
        self.assertEqual(d.status,"CANDIDATE_READY_FOR_REVIEW")
        self.assertEqual(d.provider_writes,0)
    def test_stale_constitution_blocks(self):
        self.assertEqual(self.decide(revision="rev3").reason,"STALE_CONSTITUTION")
    def test_contradiction_blocks(self):
        c=candidate();c["contradiction_refs"]=["c1"]
        self.assertEqual(self.decide(c).reason,"UNRESOLVED_CONTRADICTION")
    def test_permission_escalation_blocks(self):
        c=candidate();c["permissions"]=["admin"]
        self.assertEqual(self.decide(c).reason,"AUTHORITY_BOUNDARY")
    def test_missing_provenance_blocks(self):
        c=candidate();c["evidence_refs"]=[]
        self.assertEqual(self.decide(c).reason,"MISSING_EVIDENCE")
    def test_duplicate_source_blocks(self):
        c=candidate();c["source_refs"]=["source1","source1"]
        self.assertEqual(self.decide(c).reason,"DUPLICATE_SOURCE")
    def test_recipients_deduplicated(self):
        self.assertEqual(self.decide(recipients=["planning","research","planning"]).recipients,("planning","research"))
    def test_empty_recipients_blocks(self):
        self.assertEqual(self.decide(recipients=[]).reason,"NO_RECIPIENTS")

if __name__=="__main__":
    unittest.main()
