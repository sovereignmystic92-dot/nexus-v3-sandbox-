import unittest
from nexus_sandbox.journal_recovery_decision import decide_recovery


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "schema": "nexus.journal.host-readiness.v1",
            "verdict": "LOCAL_JOURNAL_OBSERVED_NOT_ACTIVATED",
            "journal": {
                "status": "OBSERVED_EXISTING",
                "identity_match": True,
                "integrity": "ok",
                "pending_or_held": 1,
            },
        }

    def test_verified_local_journal_is_not_enough(self):
        self.assertEqual(decide_recovery(self.report)["reason"],
                         "EXCLUSIVE_CUSTODY_UNPROVEN")

    def test_missing_custody_holds(self):
        self.assertEqual(decide_recovery(
            self.report, source_reobserved=True, effect_reconciled=True)["decision"], "HOLD")

    def test_unreobserved_source_holds(self):
        self.assertEqual(decide_recovery(
            self.report, exclusive_custody=True, effect_reconciled=True)["reason"],
            "SOURCE_NOT_REOBSERVED")

    def test_unreconciled_effect_observe_only(self):
        self.assertEqual(decide_recovery(
            self.report, exclusive_custody=True, source_reobserved=True)["decision"],
            "OBSERVE_ONLY")

    def test_all_flags_only_enable_manual_review(self):
        self.assertEqual(decide_recovery(
            self.report, exclusive_custody=True, source_reobserved=True,
            effect_reconciled=True)["decision"], "ELIGIBLE_FOR_BOUNDED_MANUAL_REVIEW")

    def test_bad_or_missing_journal_holds(self):
        for report in ({}, {"schema": "nexus.journal.host-readiness.v1",
                            "verdict": "HOLD"}, dict(self.report, journal={})):
            self.assertEqual(decide_recovery(report)["decision"], "HOLD")

    def test_invalid_flag_rejected(self):
        with self.assertRaises(ValueError):
            decide_recovery(self.report, exclusive_custody="yes")


if __name__ == "__main__":
    unittest.main()
