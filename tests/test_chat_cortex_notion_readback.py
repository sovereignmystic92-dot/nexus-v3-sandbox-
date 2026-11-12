import unittest
from nexus_sandbox.chat_cortex_notion_readback import verify_notion_export

class NotionReadbackTests(unittest.TestCase):
    def test_rejects_missing_source(self):
        with self.assertRaises(ValueError):
            verify_notion_export("", source_id="wrong", source_revision="rev")
    def test_rejects_truncated_export(self):
        with self.assertRaises(ValueError):
            verify_notion_export("", source_id="4168c067-daa4-8111-bda6-ef07325583ed",
                                 source_revision="rev", truncated=True)
    def test_rejects_unverified_content(self):
        with self.assertRaises(ValueError):
            verify_notion_export("Pending Cortex Processing", source_id="4168c067-daa4-8111-bda6-ef07325583ed",
                                 source_revision="rev")
    def test_rejects_unknown_blocks(self):
        with self.assertRaises(ValueError):
            verify_notion_export("", source_id="4168c067-daa4-8111-bda6-ef07325583ed",
                                 source_revision="rev", unknown_block_count=1)

if __name__ == "__main__":
    unittest.main()
