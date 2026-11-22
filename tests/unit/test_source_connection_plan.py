import copy
import hashlib
import json
import unittest

from nexus_sandbox.source_connection_plan import prepare_connection_plan


class ConnectionPlanTests(unittest.TestCase):
    def setUp(self):
        self.envelope = {
            "source_url": "https://app.notion.com/p/00000000000000000000000000000001",
            "source_revision": "synthetic-revision-1",
            "document_id": "notion:00000000-0000-0000-0000-000000000001",
            "transcript": "Synthetic source.\n\nSecond paragraph. Ω",
        }
        self.envelope["expected_sha256"] = hashlib.sha256(
            self.envelope["transcript"].encode("utf-8")).hexdigest()
        self.context = dict(mission_id="synthetic-mission", code_revision="a" * 40,
                            policy_revision="synthetic-policy-1")

    def plan(self, envelope=None, **context):
        return prepare_connection_plan(
            self.envelope if envelope is None else envelope,
            **{**self.context, **context})

    def test_one_source_two_pending_consumers_without_source_text(self):
        before = copy.deepcopy(self.envelope)
        plan = self.plan()
        self.assertEqual(self.envelope, before)
        self.assertEqual([c["consumer"] for c in plan["consumers"]],
                         ["knowledge_development", "csf"])
        self.assertNotIn(self.envelope["transcript"], json.dumps(plan))
        for consumer in plan["consumers"]:
            self.assertEqual(consumer["source_key"], plan["source_key"])
            self.assertEqual(consumer["status"], "NOT_STARTED")
            self.assertIsNone(consumer["receipt_ref"])

    def test_replay_is_deterministic_and_consumer_keys_are_distinct(self):
        plan = self.plan()
        self.assertEqual(plan, self.plan(dict(reversed(list(self.envelope.items())))))
        self.assertEqual(len({c["work_key"] for c in plan["consumers"]}), 2)

    def test_revision_change_changes_shared_source_identity(self):
        changed = {**self.envelope, "source_revision": "synthetic-revision-2"}
        self.assertNotEqual(self.plan()["source_key"], self.plan(changed)["source_key"])

    def test_changed_transcript_with_recomputed_pin_changes_source_key(self):
        changed = {**self.envelope, "transcript": self.envelope["transcript"] + " "}
        changed["expected_sha256"] = hashlib.sha256(changed["transcript"].encode()).hexdigest()
        self.assertNotEqual(self.plan()["source_key"], self.plan(changed)["source_key"])

    def test_tampered_source_is_rejected(self):
        with self.assertRaises(ValueError):
            self.plan({**self.envelope, "transcript": "tampered"})

    def test_conflicting_page_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            self.plan({**self.envelope, "source_url": self.envelope["source_url"][:-1] + "2"})

    def test_invalid_or_noncanonical_page_identity_is_rejected(self):
        for page in ("other:abc", "notion:not-a-page", "notion:" + "0" * 32):
            with self.subTest(page=page), self.assertRaises(ValueError):
                self.plan({**self.envelope, "document_id": page})

    def test_policy_code_and_mission_changes_rebind_work_not_source(self):
        original = self.plan()
        for context in (dict(policy_revision="synthetic-policy-2"),
                        dict(code_revision="b" * 40), dict(mission_id="another")):
            changed = self.plan(**context)
            self.assertEqual(changed["source_key"], original["source_key"])
            self.assertNotEqual(changed["plan_id"], original["plan_id"])
            self.assertNotEqual(changed["consumers"], original["consumers"])

    def test_unknown_input_fields_and_missing_context_are_rejected(self):
        with self.assertRaises(ValueError):
            self.plan({**self.envelope, "allow_create": True})
        for context in (dict(mission_id=""), dict(policy_revision=" "),
                        dict(code_revision="main"), dict(code_revision=True)):
            with self.subTest(context=context), self.assertRaises(ValueError):
                self.plan(**context)

    def test_plan_never_claims_authentication_execution_or_promotion(self):
        plan = self.plan()
        self.assertEqual(plan["status"], "PLAN_ONLY")
        self.assertEqual(plan["source_integrity_status"],
                         "LOCAL_DIGEST_MATCHED_NOT_AUTHENTICATED")
        self.assertEqual(plan["external_writes"], 0)
        for field in ("provider_called", "approved_for_persistence", "audit_gate_promoted"):
            self.assertIs(plan[field], False)


if __name__ == "__main__":
    unittest.main()
