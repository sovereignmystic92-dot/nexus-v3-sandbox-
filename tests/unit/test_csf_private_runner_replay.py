"""Credential-free checks of the private replay boundary."""
import base64
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("private_replay", ROOT / "tools/csf_private_runner_replay.py")
replay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay)


class PrivateReplayTests(unittest.TestCase):
    def test_missing_corrupt_and_oversized_batches_never_fetch_source(self):
        source_loader = Mock()
        for value in (None, "", "!", "x" * 24001, base64.b64encode(b"wrong database").decode()):
            with self.subTest(value_type=type(value).__name__), self.assertRaises((ValueError, TypeError)):
                replay.recover(value, source_loader, ROOT)
        source_loader.assert_not_called()

    def test_source_revision_and_identity_rejected(self):
        source = {"source_url": replay.SOURCE_URL, "source_revision": replay.REVISION,
                  "document_id": "notion:" + replay.PAGE_ID,
                  "expected_sha256": replay.SOURCE_SHA256, "transcript": "fictional"}
        for key in ("source_url", "source_revision", "document_id", "expected_sha256", "transcript"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                replay.validate_source(dict(source, **{key: "changed"}))

    def test_reordered_refs_match_but_stale_duplicate_and_missing_refs_fail(self):
        result = {"status": "BATCH_REPLAYED", "finding_count": 3,
                  "provider_called": False, "audit_gate_promoted": False,
                  "finding_refs": list(reversed(replay.EXPECTED_REFS))}
        self.assertEqual(replay.validate_result(result)["finding_count"], 3)
        stale = [dict(item) for item in replay.EXPECTED_REFS]
        stale[0]["payload_sha256"] = "0" * 64
        for refs in (stale, replay.EXPECTED_REFS[:2], [replay.EXPECTED_REFS[0]] * 3):
            with self.subTest(refs=refs), self.assertRaises(ValueError):
                replay.validate_result(dict(result, finding_refs=refs))

    def test_unexpected_child_fields_are_not_emitted(self):
        result = {"status": "BATCH_REPLAYED", "finding_count": 3,
                  "provider_called": False, "audit_gate_promoted": False,
                  "finding_refs": replay.EXPECTED_REFS, "transcript": "PRIVATE_MARKER"}
        self.assertNotIn("PRIVATE_MARKER", json.dumps(replay.validate_result(result)))

    def test_main_blocks_nonmanual_context_without_loading_source(self):
        with patch.dict(replay.os.environ, {}, clear=True), patch.object(replay, "fetch_source") as fetch:
            self.assertEqual(replay.main(), 2)
            fetch.assert_not_called()

    def test_provider_and_audit_flags_must_be_false(self):
        result = {"status": "BATCH_REPLAYED", "finding_count": 3,
                  "provider_called": False, "audit_gate_promoted": False,
                  "finding_refs": replay.EXPECTED_REFS}
        for key in ("provider_called", "audit_gate_promoted"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                replay.validate_result(dict(result, **{key: True}))


if __name__ == "__main__":
    unittest.main()
