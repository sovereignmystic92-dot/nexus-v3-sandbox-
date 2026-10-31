import unittest

from nexus_sandbox.cortex_pilot_receipt import verify_cortex_pilot

S = "a" * 64

class PilotReceiptTests(unittest.TestCase):
    def setUp(self):
        self.route = dict(source_kind="TRANSCRIPT", source_store="NOTION",
            source_id="notion:source:1", source_revision="v1",
            source_sha256=S, output_kind="NEXUS_OUTPUT", output_store="CORTEX",
            output_id="cortex:output:1", output_revision="r1",
            output_source_id="notion:source:1", output_source_sha256=S)
        self.output = dict(output_id="cortex:output:1",
            source_id="notion:source:1",source_sha256=S,
            revision="r1",analysis="Supported evidence and open questions")

    def check(self, **changes):
        args=dict(route=self.route,expected_output=self.output,
            observed_output=dict(self.output),source_verified=True,
            authority_verified=True,output_inventory_complete=True)
        args.update(changes)
        return verify_cortex_pilot(**args)

    def test_matching_snapshot_only_reports_readback(self):
        r=self.check()
        self.assertEqual(r.status,"READBACK_MATCHED")
        self.assertEqual(r.provider_writes,0)
        self.assertFalse(r.automatic_execution)
        self.assertEqual(r.cp09,"NOT_PROVEN")
        self.assertEqual(len(r.output_sha256),64)

    def test_missing_archive_verification_blocks(self):
        self.assertEqual(self.check(source_verified=False).status,"BLOCKED")

    def test_unverified_cortex_authority_blocks(self):
        self.assertEqual(self.check(authority_verified=False).status,"BLOCKED")

    def test_incomplete_cortex_snapshot_blocks(self):
        self.assertEqual(self.check(output_inventory_complete=False).status,"BLOCKED")

    def test_mismatch_blocks_without_replay(self):
        modified=dict(self.output,analysis="Different")
        self.assertEqual(self.check(observed_output=modified).next_action,
            "RECONCILE_UNCERTAIN_CORTEX_WRITE_NO_RETRY")

    def test_notional_output_destination_rejected(self):
        route=dict(self.route,output_store="NOTION")
        self.assertEqual(self.check(route=route).status,"BLOCKED")

    def test_wrong_source_digest_rejected(self):
        route=dict(self.route,output_source_sha256="b"*64)
        self.assertEqual(self.check(route=route).status,"BLOCKED")

    def test_wrong_output_identity_rejected(self):
        modified=dict(self.output,output_id="cortex:other")
        self.assertEqual(self.check(expected_output=modified).status,"BLOCKED")

    def test_missing_fields_rejected(self):
        modified=dict(self.output)
        modified.pop("analysis")
        self.assertEqual(self.check(observed_output=modified).status,"BLOCKED")

    def test_boolean_string_fails_closed(self):
        self.assertEqual(self.check(authority_verified="true").status,"BLOCKED")

    def test_changed_revision_requires_reconciliation(self):
        modified=dict(self.output,revision="r2")
        self.assertEqual(self.check(expected_output=modified).status,"BLOCKED")


if __name__=="__main__":
    unittest.main()
