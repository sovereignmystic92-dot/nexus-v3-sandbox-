"""No-effect Notion-source/Cortex-output event intake checks."""
import tempfile
from pathlib import Path
import unittest

from nexus_sandbox.event_router import Event, Enrollment, ObserverQueue
from nexus_sandbox.transcript_completion import SourceSnapshot, source_digest
from nexus_sandbox.transcript_cortex_intake import prepare_transcript_inspection


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.queue = ObserverQueue(Path(self.tmp.name)/'events.sqlite',initialize=True)
        self.source = SourceSnapshot('notion:transcript:one','notion:archive',
                          (('segment1','A full transcript sample'),),True)
        self.digest = source_digest(self.source)
        self.route = dict(source_kind='TRANSCRIPT',source_store='NOTION',
            source_id=self.source.page_id,source_revision='v1',
            source_sha256=self.digest,output_kind='NEXUS_OUTPUT',
            output_store='CORTEX',output_id='cortex:output:one',
            output_revision='v1',output_source_id=self.source.page_id,
            output_source_sha256=self.digest)
        self.event = Event('evt-one','SOURCE_READY',self.source.page_id,
                           self.digest,'SOURCE')
        self.enrollment = Enrollment(self.source.page_id,'policy-v1',
            'code-v1','synthetic-auth',('INSPECT_TRANSCRIPT',),30)

    def call(self, **updates):
        v=dict(source=self.source,route_record=self.route,event=self.event,
               enrollment=self.enrollment,queue=self.queue,
               archive_readback_verified=True,event_authenticated=True,
               source_revision_verified=True,cortex_authority_verified=True)
        v.update(updates)
        return prepare_transcript_inspection(**v)

    def test_verified_source_plans_inspection_not_execution(self):
        r=self.call()
        self.assertEqual(r.status,'PLANNED')
        self.assertTrue(r.job_id)
        self.assertEqual(r.provider_writes,0)
        self.assertFalse(r.automatic_execution)

    def test_repeat_cannot_create_duplicate_job(self):
        first=self.call(); second=self.call()
        self.assertEqual(second.status,'DUPLICATE')
        self.assertEqual(first.job_id,second.job_id)

    def test_notion_output_destination_rejected(self):
        r=dict(self.route,output_store='NOTION')
        self.assertEqual(self.call(route_record=r).status,'BLOCKED')

    def test_wrong_source_digest_rejected(self):
        r=dict(self.route,source_sha256='0'*64)
        self.assertEqual(self.call(route_record=r).next_action,
                         'RECONCILE_NOTION_SOURCE_BINDING')

    def test_unverified_source_readback_blocks(self):
        self.assertEqual(self.call(archive_readback_verified=False).status,'BLOCKED')

    def test_event_without_host_authentication_blocks(self):
        self.assertEqual(self.call(event_authenticated=False).status,'BLOCKED')

    def test_revision_unverified_blocks(self):
        self.assertEqual(self.call(source_revision_verified=False).status,'BLOCKED')

    def test_cortex_authority_unverified_blocks(self):
        self.assertEqual(self.call(cortex_authority_verified=False).status,'BLOCKED')

    def test_string_assertion_rejected(self):
        self.assertEqual(self.call(event_authenticated='true').status,'BLOCKED')

    def test_unexpected_source_revision_event_rejected(self):
        event=Event('evt-one','SOURCE_READY',self.source.page_id,'f'*64,'SOURCE')
        self.assertEqual(self.call(event=event).status,'BLOCKED')

    def test_not_full_transcript_blocks(self):
        src=SourceSnapshot(self.source.page_id,self.source.parent_id,
                           self.source.segments,False)
        self.assertEqual(self.call(source=src).status,'BLOCKED')

    def test_output_bindings_must_match(self):
        r=dict(self.route,output_source_id='notion:transcript:other')
        self.assertEqual(self.call(route_record=r).status,'BLOCKED')

    def test_enrollment_does_not_grant_execution(self):
        enrollment=Enrollment(self.source.page_id,'policy-v1',
            'code-v1','synthetic-auth',('DIAGNOSE_CHECK',),30)
        self.assertEqual(self.call(enrollment=enrollment).status,'BLOCKED')


if __name__=='__main__':
    unittest.main()
