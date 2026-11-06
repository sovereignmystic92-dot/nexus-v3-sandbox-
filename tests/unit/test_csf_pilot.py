"""Synthetic-only CSF contract tests; no external systems are contacted."""
import copy
import hashlib
import unittest

from nexus_sandbox.csf_pilot import (
    ContractError, authorize_transition, stable_key, validate,
)


def sample():
    transcript = b"synthetic governance and infrastructure transcript"
    source = {"id": "synthetic-haiti", "revision": "r1",
              "digest": hashlib.sha256(transcript).hexdigest(),
              "notion_ref": "synthetic://notion/haiti"}
    return {
        "contract_version": "0.1.0", "source": source, "target": None,
        "claim_id": "claim-1", "claim_type": "observation",
        "domains": ["governance", "infrastructure"],
        "statement": "A source reports an infrastructure disruption.",
        "evidence": [{"ref": "synthetic://notion/haiti#offset=0"}],
        "relations": [], "uncertainty": {"level": "unverified", "reason": "source claim"},
        "counterevidence": "not_checked",
        "review": {"status": "pending", "reviewer": None},
        "idempotency_key": stable_key("synthetic-haiti", "r1", "claim-1"),
    }


class CSFPilotTests(unittest.TestCase):
    def test_valid_dry_run_does_not_mutate_record(self):
        record = sample()
        before = copy.deepcopy(record)
        self.assertTrue(validate(record))
        self.assertEqual(record, before)

    def test_repeat_is_idempotent(self):
        self.assertEqual(sample()["idempotency_key"], sample()["idempotency_key"])

    def test_observation_without_evidence_rejected(self):
        record = sample()
        record["evidence"] = []
        with self.assertRaises(ContractError):
            validate(record)

    def test_unknown_version_rejected(self):
        record = sample()
        record["contract_version"] = "0.2.0"
        with self.assertRaises(ContractError):
            validate(record)

    def test_invalid_domain_rejected(self):
        record = sample()
        record["domains"] = ["fiction"]
        with self.assertRaises(ContractError):
            validate(record)

    def test_wrong_idempotency_key_rejected(self):
        record = sample()
        record["idempotency_key"] = "invalid"
        with self.assertRaises(ContractError):
            validate(record)

    def test_review_cannot_self_certify(self):
        with self.assertRaises(ContractError):
            authorize_transition("TESTED", "INDEPENDENT_REVIEWED",
                                 actor="Gemini", evidence_ref="synthetic://review",
                                 proposer="Gemini", reviewer="Gemini")

    def test_independent_review_transition(self):
        self.assertEqual(authorize_transition("TESTED", "INDEPENDENT_REVIEWED",
                         actor="Gemini", evidence_ref="synthetic://review",
                         proposer="Chat", reviewer="Gemini"), "INDEPENDENT_REVIEWED")

    def test_missing_target_blocks_persistence(self):
        with self.assertRaises(ContractError):
            authorize_transition("OWNER_APPROVED", "PERSISTED",
                                 actor="worker", evidence_ref="synthetic://run",
                                 target=None, write_authorized=True)

    def test_unapproved_write_blocks_persistence(self):
        with self.assertRaises(ContractError):
            authorize_transition("OWNER_APPROVED", "PERSISTED",
                                 actor="worker", evidence_ref="synthetic://run",
                                 target={"module_id": "existing", "revision": "r1"},
                                 write_authorized=False)

    def test_skipped_state_rejected(self):
        with self.assertRaises(ContractError):
            authorize_transition("SOURCE_VERIFIED", "TESTED",
                                 actor="worker", evidence_ref="synthetic://run")


if __name__ == "__main__":
    unittest.main()
