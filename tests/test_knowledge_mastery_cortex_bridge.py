"""Offline tests for Cortex mastery routing; no provider operations."""
import unittest
from nexus_sandbox.knowledge_mastery_cortex_bridge import prepare_mastery_handoff

def route():
    digest="a"*64
    return dict(source_kind="TRANSCRIPT",source_store="NOTION",
                source_id="notion:1",source_revision="r1",source_sha256=digest,
                output_kind="NEXUS_OUTPUT",output_store="CORTEX",
                output_id="cortex:1",output_revision="r1",
                output_source_id="notion:1",output_source_sha256=digest)

def assessment(level=2):
    return dict(status="candidate_only",demonstrated_level=level,
                accepted_evaluation_ids=["eval-1"])

class MasteryCortexBridgeTests(unittest.TestCase):
    def prepare(self, a=None, r=None, archive=True, authority=True):
        return prepare_mastery_handoff(assessment=assessment() if a is None else a,
              route_record=route() if r is None else r,
              archive_readback_verified=archive,
              cortex_authority_verified=authority)
    def test_valid_route_is_not_persistence(self):
        d=self.prepare()
        self.assertEqual(d.status,"CANDIDATE_ROUTED_NOT_PERSISTED")
        self.assertEqual(d.provider_writes,0)
        self.assertFalse(d.completion_verified)
    def test_unverified_archive_blocks(self):
        self.assertEqual(self.prepare(archive=False).status,"BLOCKED")
    def test_unverified_cortex_authority_blocks(self):
        self.assertEqual(self.prepare(authority=False).status,"BLOCKED")
    def test_wrong_destination_blocks(self):
        r=route();r["output_store"]="NOTION"
        self.assertEqual(self.prepare(r=r).status,"BLOCKED")
    def test_missing_mastery_blocks(self):
        self.assertEqual(self.prepare(a=assessment(0)).status,"BLOCKED")
    def test_unrecognized_assessment_blocks(self):
        a=assessment();a["status"]="promoted"
        self.assertEqual(self.prepare(a=a).status,"BLOCKED")

if __name__=="__main__":
    unittest.main()
