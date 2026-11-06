"""CP05 Notion display URL identity checks; offline only."""
import unittest
from nexus_sandbox.cp05_notion_identity import notion_page_matches

ID = "40b8c067daa481a3bc7ee289c8f7f050"
BASE = "https://app.notion.com/p/" + ID

class NotionIdentityTests(unittest.TestCase):
    def test_exact_canonical(self):
        self.assertTrue(notion_page_matches(BASE, ID))
    def test_display_query_parameter(self):
        self.assertTrue(notion_page_matches(BASE + "?pvs=204", ID))
    def test_multiple_display_parameters(self):
        self.assertTrue(notion_page_matches(BASE + "?pvs=204&foo=bar", ID))
    def test_other_page_rejected(self):
        self.assertFalse(notion_page_matches(BASE[:-1] + "1", ID))
    def test_subdomain_spoof_rejected(self):
        self.assertFalse(notion_page_matches(BASE.replace("app.notion.com", "app.notion.com.evil.test"), ID))
    def test_scheme_downgrade_rejected(self):
        self.assertFalse(notion_page_matches(BASE.replace("https:", "http:"), ID))
    def test_port_rejected(self):
        self.assertFalse(notion_page_matches(BASE.replace("app.notion.com", "app.notion.com:443"), ID))
    def test_path_suffix_rejected(self):
        self.assertFalse(notion_page_matches(BASE + "/other", ID))
    def test_fragment_rejected(self):
        self.assertFalse(notion_page_matches(BASE + "#other", ID))
    def test_credentials_rejected(self):
        self.assertFalse(notion_page_matches(BASE.replace("app.notion.com", "user@app.notion.com"), ID))
    def test_invalid_expected_id(self):
        self.assertFalse(notion_page_matches(BASE, "bad"))
    def test_nonstring_rejected(self):
        self.assertFalse(notion_page_matches(None, ID))

if __name__ == "__main__":
    unittest.main()
