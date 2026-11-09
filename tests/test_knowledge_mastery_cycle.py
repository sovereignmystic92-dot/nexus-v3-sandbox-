import unittest
from nexus_sandbox.knowledge_mastery_cycle import prepare_learning_cycle

def fixture():
    d="a"*64
    route=dict(source_kind="TRANSCRIPT",source_store="NOTION",source_id="notion:1",
        source_revision="r1",source_sha256=d,output_kind="NEXUS_OUTPUT",
        output_store="CORTEX",output_id="cortex:1",output_revision="r1",
        output_source_id="notion:1",output_source_sha256=d)
    assessment=dict(subject_id="topic",status="candidate_only",
        demonstrated_level=2,accepted_evaluation_ids=["e1"])
    candidate=dict(subject_id="topic",source_refs=["s1"],evidence_refs=["proof"],
        evaluation_ids=["e1"],constitution_revision="rev2",contradiction_refs=[],
        mastery_level=2)
    history=[dict(record_id="r1",revision=1,supersedes=[],source_refs=["s1"],
        evidence_refs=["proof"],constitution_revision="rev2",
        review_independence_status="verified",contradiction_refs=[])]
    return dict(assessment=assessment,route_record=route,candidate=candidate,
        recipient_modules=["research"],history_records=history,
        active_constitution_revision="rev2",archive_readback_verified=True,
        cortex_authority_verified=True)

class LearningCycleTests(unittest.TestCase):
    def test_cycle_is_candidate_only(self):
        d=prepare_learning_cycle(**fixture())
        self.assertEqual(d.status,"CANDIDATE_READY_FOR_EXTERNAL_REVIEW")
        self.assertEqual(d.provider_writes,0)
        self.assertEqual(d.constitutional_changes,0)
    def test_subject_mismatch_blocks(self):
        f=fixture();f["candidate"]["subject_id"]="other"
        self.assertEqual(prepare_learning_cycle(**f).next_action,"SUBJECT_BINDING_MISMATCH")
    def test_level_mismatch_blocks(self):
        f=fixture();f["candidate"]["mastery_level"]=5
        self.assertEqual(prepare_learning_cycle(**f).next_action,"MASTERY_LEVEL_MISMATCH")
    def test_evaluation_mismatch_blocks(self):
        f=fixture();f["candidate"]["evaluation_ids"]=["unreviewed"]
        self.assertEqual(prepare_learning_cycle(**f).next_action,"EVALUATION_BINDING_MISMATCH")
    def test_missing_cortex_authority_blocks(self):
        f=fixture();f["cortex_authority_verified"]=False
        self.assertEqual(prepare_learning_cycle(**f).status,"BLOCKED")
    def test_unresolved_history_blocks(self):
        f=fixture();f["history_records"][0]["contradiction_refs"]=["c1"]
        self.assertEqual(prepare_learning_cycle(**f).status,"BLOCKED")
    def test_stale_constitution_blocks(self):
        f=fixture();f["active_constitution_revision"]="rev3"
        self.assertEqual(prepare_learning_cycle(**f).status,"BLOCKED")

if __name__=="__main__":
    unittest.main()
