import unittest
from nexus_sandbox.warfronts_source_transfer import extract_episode, fetch_episode, START, END

class WarFrontsSourceTransferTests(unittest.TestCase):
    def test_extracts_main_and_excludes_promotion(self):
        body = START + " " + ("discussion " * 250) + END
        html = "<html><main><p>" + body + "</p><p>Brain Food Show promotional content</p></main></html>"
        result = extract_episode(html)
        self.assertTrue(result.startswith(START))
        self.assertTrue(result.endswith(END))
        self.assertNotIn("Brain Food Show", result)
    def test_missing_ending_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_episode("<p>" + START + " " + ("text " * 300) + "</p>")
    def test_missing_opening_fails_closed(self):
        with self.assertRaises(ValueError):
            extract_episode("<p>" + ("text " * 300) + END + "</p>")
    def test_disallows_arbitrary_url(self):
        with self.assertRaises(ValueError):
            fetch_episode("https://example.com")
