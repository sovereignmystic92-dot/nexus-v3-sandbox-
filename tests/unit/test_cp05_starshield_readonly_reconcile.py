"""CP05 read-only Starshield source/Cortex identity reconciliation contract.

Offline regression fixture: values observed independently from Notion and Cortex.
This does not invoke either provider, write anything, or prove live adapter coverage.
"""
import unittest

SOURCE_ID = "40b8c067daa481a3bc7ee289c8f7f050"
VIDEO_ID = "kokDVXUGdes"
MODULE_ID = "module_01m6b6fdsz1s0ma4rqhvbdpe10"
EXPECTED_REVISION = 1
SOURCE_URL = "https://app.notion.com/p/" + SOURCE_ID
VIDEO_URL = "https://youtu.be/" + VIDEO_ID

def reconcile(source, module):
    """Fail closed on identity, revision, source fidelity, or duplicate ambiguity."""
    if source.get("id") != SOURCE_ID or source.get("video_id") != VIDEO_ID:
        return "BLOCKED_SOURCE_IDENTITY"
    if source.get("verbatim") is not False:
        return "BLOCKED_FIDELITY_UNVERIFIED"
    if module.get("id") != MODULE_ID or module.get("version") != EXPECTED_REVISION:
        return "BLOCKED_MODULE_REVISION"
    if SOURCE_URL not in module.get("content", "") or VIDEO_URL not in module.get("content", ""):
        return "BLOCKED_PROVENANCE"
    if module.get("matching_module_count") != 1:
        return "BLOCKED_DUPLICATE_AMBIGUITY"
    return "MATCHED_EXISTING_READ_ONLY_SOURCE_NOT_VERBATIM"

class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.source = {"id": SOURCE_ID, "video_id": VIDEO_ID, "verbatim": False}
        self.module = {"id": MODULE_ID, "version": 1,
                       "content": SOURCE_URL + "\n" + VIDEO_URL,
                       "matching_module_count": 1}

    def test_matching_pair(self):
        self.assertEqual(reconcile(self.source, self.module),
                         "MATCHED_EXISTING_READ_ONLY_SOURCE_NOT_VERBATIM")

    def test_wrong_source(self):
        self.source["id"] = "other"
        self.assertEqual(reconcile(self.source, self.module), "BLOCKED_SOURCE_IDENTITY")

    def test_revision_drift(self):
        self.module["version"] = 2
        self.assertEqual(reconcile(self.source, self.module), "BLOCKED_MODULE_REVISION")

    def test_missing_provenance(self):
        self.module["content"] = VIDEO_URL
        self.assertEqual(reconcile(self.source, self.module), "BLOCKED_PROVENANCE")

    def test_duplicate_candidates(self):
        self.module["matching_module_count"] = 2
        self.assertEqual(reconcile(self.source, self.module), "BLOCKED_DUPLICATE_AMBIGUITY")

    def test_unverified_fidelity_claim(self):
        self.source["verbatim"] = True
        self.assertEqual(reconcile(self.source, self.module), "BLOCKED_FIDELITY_UNVERIFIED")

if __name__ == "__main__":
    unittest.main()
