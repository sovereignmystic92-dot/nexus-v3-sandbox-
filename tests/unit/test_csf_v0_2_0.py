"""Gates A/B/E synthetic CSF v0.2 tests (offline)."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from nexus_sandbox.csf_v02 import (
    CSFValidationError, deduplicate, generate_finding_id,
    generate_idempotency_key, make_finding, validate_finding,
)

ROOT = Path(__file__).resolve().parents[2]
SEGMENT = "Synthetic source states that port access was interrupted."


def sample():
    return make_finding("synthetic-haiti", "seg-1", SEGMENT,
                        "Port access interruption was reported.",
                        "inf_supply", "observation", "structural_bottleneck")


class CSFv02Tests(unittest.TestCase):
    def test_gate_a_schema_exists_and_strict(self):
        schema = json.loads((ROOT / "schemas/csf_schema_v0.2.0.json").read_text())
        self.assertEqual(schema["properties"]["contract_version"]["const"], "0.2.0")
        self.assertFalse(schema["additionalProperties"])
        self.assertFalse(schema["properties"]["source_reference"]["additionalProperties"])
        self.assertFalse(schema["properties"]["causal_links"]["items"]["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(sample()))

    def test_gate_a_valid(self):
        self.assertTrue(validate_finding(sample(), {"seg-1": SEGMENT}))

    def test_gate_a_unknown_field(self):
        record = sample()
        record["surprise"] = True
        with self.assertRaises(CSFValidationError):
            validate_finding(record)

    def test_gate_a_missing_confidence(self):
        record = sample()
        del record["confidence_level"]
        with self.assertRaises(CSFValidationError):
            validate_finding(record)

    def test_gate_a_missing_verification_status(self):
        record = sample()
        record["causal_links"] = [{"target_domain": "gov_coordination",
                                   "direction": "constrains", "mechanism": "test",
                                   "evidence_refs": ["seg-1"]}]
        with self.assertRaises(CSFValidationError):
            validate_finding(record)

    def test_gate_b_orphan_domain(self):
        record = sample()
        record["causal_links"] = [{"target_domain": "unknown", "direction": "constrains",
                                   "mechanism": "test", "evidence_refs": ["seg-1"],
                                   "verification_status": "hypothesized"}]
        with self.assertRaises(CSFValidationError):
            validate_finding(record, {"seg-1": SEGMENT})

    def test_gate_b_orphan_segment(self):
        record = sample()
        record["causal_links"] = [{"target_domain": "gov_coordination",
                                   "direction": "constrains", "mechanism": "test",
                                   "evidence_refs": ["missing"],
                                   "verification_status": "hypothesized"}]
        with self.assertRaises(CSFValidationError):
            validate_finding(record, {"seg-1": SEGMENT})

    def test_gate_b_verified_link(self):
        record = sample()
        record["causal_links"] = [{"target_domain": "gov_coordination",
                                   "direction": "constrains", "mechanism": "hypothesis only",
                                   "evidence_refs": ["seg-1"],
                                   "verification_status": "hypothesized"}]
        self.assertTrue(validate_finding(record, {"seg-1": SEGMENT}))

    def test_gate_e_stable_identity_and_upsert(self):
        first = sample()
        second = sample()
        self.assertEqual(first["finding_id"], second["finding_id"])
        self.assertEqual(first["idempotency_key"], second["idempotency_key"])
        self.assertEqual(len(deduplicate([first, second])), 1)

    def test_gate_e_normalized_assertion(self):
        digest = hashlib.sha256(SEGMENT.encode()).hexdigest()
        a = generate_idempotency_key("synthetic-haiti", digest, "  PORT ACCESS  ")
        b = generate_idempotency_key("synthetic-haiti", digest, "port access")
        self.assertEqual(a, b)
        self.assertEqual(generate_finding_id(a), generate_finding_id(b))

    def test_gate_e_conflict_detected(self):
        record = sample()
        conflicting = copy.deepcopy(record)
        conflicting["confidence_level"] = "high"
        with self.assertRaises(CSFValidationError):
            deduplicate([record, conflicting])

    def test_gate_e_does_not_mutate_input(self):
        record = sample()
        original = copy.deepcopy(record)
        validate_finding(record)
        deduplicate([record, record])
        self.assertEqual(record, original)


if __name__ == "__main__":
    unittest.main()
