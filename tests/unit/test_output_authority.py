"""Routing rules must reject historical Notion-output destinations."""
import unittest
from nexus_sandbox.output_authority import (
    validate_output_route, legacy_notion_output_disposition
)

DIGEST = 'a' * 64


def valid():
    return dict(source_kind='TRANSCRIPT', source_store='NOTION',
                source_id='notion:transcript:01', source_revision='v1',
                source_sha256=DIGEST, output_kind='NEXUS_OUTPUT',
                output_store='CORTEX', output_id='cortex:output:01',
                output_revision='v1', output_source_id='notion:transcript:01',
                output_source_sha256=DIGEST)


class OutputAuthorityTests(unittest.TestCase):
    def assess(self, item, **flags):
        defaults=dict(archive_readback_verified=True,
                      cortex_authority_verified=True,
                      cortex_output_readback_verified=True)
        defaults.update(flags)
        return validate_output_route(item, **defaults)

    def test_correct_route_requires_remaining_processing_checks(self):
        v=self.assess(valid())
        self.assertEqual((v.status,v.next_action),
                         ('ROUTE_VERIFIED','CHECK_REMAINING_PROCESSING_GATES'))
        self.assertFalse(v.ready_to_write)

    def test_legacy_notion_output_rejected(self):
        r=valid();r['output_store']='NOTION'
        self.assertEqual(self.assess(r).next_action,'ROUTE_NEXUS_OUTPUT_TO_CORTEX')

    def test_cortex_transcript_source_not_accepted(self):
        r=valid();r['source_store']='CORTEX'
        self.assertEqual(self.assess(r).status,'BLOCKED')

    def test_wrong_source_link_blocks(self):
        r=valid();r['output_source_id']='notion:transcript:02'
        self.assertEqual(self.assess(r).next_action,'RECONCILE_SOURCE_OUTPUT_LINK')

    def test_wrong_digest_blocks(self):
        r=valid();r['output_source_sha256']='b'*64
        self.assertEqual(self.assess(r).status,'BLOCKED')

    def test_missing_archive_readback_blocks(self):
        self.assertEqual(self.assess(valid(),archive_readback_verified=False).status,'BLOCKED')

    def test_missing_cortex_authority_blocks(self):
        self.assertEqual(self.assess(valid(),cortex_authority_verified=False).status,'BLOCKED')

    def test_missing_cortex_readback_holds_completion(self):
        r=self.assess(valid(),cortex_output_readback_verified=False)
        self.assertEqual(r.status,'ROUTED_NOT_COMPLETE')
        self.assertFalse(r.completion_verified)

    def test_authority_flag_cannot_be_string(self):
        self.assertEqual(self.assess(valid(),cortex_authority_verified='yes').status,'BLOCKED')

    def test_unknown_schema_field_rejected(self):
        r=valid();r['owner_permission']=True
        self.assertEqual(self.assess(r).status,'BLOCKED')

    def test_legacy_output_requires_migration_review(self):
        self.assertEqual(legacy_notion_output_disposition(source_bound=True,
              cortex_equivalent_verified=False),'MIGRATION_REVIEW_REQUIRED')

    def test_legacy_output_retained_when_migrated(self):
        self.assertEqual(legacy_notion_output_disposition(source_bound=True,
              cortex_equivalent_verified=True),'PRESERVE_NOTION_LEGACY_AS_PROVENANCE')

    def test_legacy_unbound_deferred(self):
        self.assertEqual(legacy_notion_output_disposition(source_bound=False,
              cortex_equivalent_verified=False),'DEFER_SOURCE_RECONCILIATION')


if __name__ == '__main__':
    unittest.main()
