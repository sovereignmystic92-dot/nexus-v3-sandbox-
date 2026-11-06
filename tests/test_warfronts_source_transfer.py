import unittest
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from nexus_sandbox.warfronts_source_transfer import extract_episode, fetch_episode, START, END, main, validate_candidate_export

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

    def test_offline_file_comparison_preserves_crlf_and_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            original = root / "original.txt"
            candidate = root / "candidate.txt"
            report = root / "report.json"
            original.write_bytes(b"alpha\r\nbeta\r\n")
            candidate.write_bytes(b"alpha\nbeta\n")
            with patch.object(sys, "argv", ["probe", "--notion-raw-file", str(original),
                    "--candidate-file", str(candidate), "--candidate-provenance", "manual:reviewed-export",
                    "--report", str(report)]):
                main()
            result = json.loads(report.read_bytes().decode("utf-8"))
            self.assertFalse(result["identical"])
            self.assertEqual(result["original_utf16_units"], 13)
            self.assertEqual(result["candidate_utf16_units"], 11)
            self.assertEqual(result["status"], "REVIEW_REQUIRED_NOT_AUTHORIZED")

    def test_manual_export_rejects_trailing_podcast_promotion(self):
        episode = START + " " + ("analysis " * 220) + END
        with self.assertRaises(ValueError):
            validate_candidate_export(episode + " Brain Food Show")
        self.assertEqual(validate_candidate_export(episode), episode)

    def test_manual_export_rejects_missing_start_or_end(self):
        episode = START + " " + ("analysis " * 220) + END
        for candidate in (episode[10:], episode[:-10], "", episode + END):
            with self.subTest(candidate_length=len(candidate)):
                with self.assertRaises(ValueError):
                    validate_candidate_export(candidate)

    def test_candidate_file_requires_explicit_provenance(self):
        with patch.object(sys, "argv", ["probe", "--notion-raw-file", "x",
                "--candidate-file", "y", "--report", "z"]):
            with self.assertRaises(SystemExit):
                main()
