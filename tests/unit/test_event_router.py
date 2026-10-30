from dataclasses import replace
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nexus_sandbox.event_router import Enrollment, Event, ObserverQueue


class EventRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'queue.sqlite'
        self.queue = ObserverQueue(self.path, initialize=True)
        self.event = Event('synthetic:event:1', 'SOURCE_READY', 'synthetic:source', 'a'*64, 'SOURCE')
        self.enrollment = Enrollment('synthetic:source', 'synthetic:policy:v1',
            'synthetic:code:v1', 'synthetic:authority',
            ('INSPECT_TRANSCRIPT', 'DIAGNOSE_CHECK', 'INSPECT_CHECKPOINT'), 10)

    def route(self, event=None, enrollment=None):
        return self.queue.route(event or self.event, enrollment or self.enrollment)

    def test_explicit_routes_only_plan(self):
        for index, (kind, action) in enumerate((('SOURCE_READY', 'INSPECT_TRANSCRIPT'),
                ('CHECK_FAILED', 'DIAGNOSE_CHECK'), ('JOB_INTERRUPTED', 'INSPECT_CHECKPOINT'))):
            result = self.route(replace(self.event, event_id=str(index), kind=kind))
            self.assertEqual((result.status, result.action), ('PLANNED', action))
        with sqlite3.connect(self.path) as db:
            for row in db.execute('SELECT binding FROM jobs'):
                self.assertIn('"provider_writes":0', row[0])
                self.assertIn('"execution_mode":"OBSERVE_ONLY"', row[0])

    def test_duplicate_event_and_alias_after_reopen(self):
        first = self.route()
        self.queue = ObserverQueue(self.path)
        self.assertEqual(self.route().status, 'DUPLICATE')
        alias = self.route(replace(self.event, event_id='alias', kind='SOURCE_REVISION_CHANGED'))
        self.assertEqual((alias.status, alias.job_id), ('DUPLICATE', first.job_id))

    def test_new_revision_has_distinct_plan(self):
        first = self.route()
        second = self.route(replace(self.event, event_id='new', revision_sha256='b'*64))
        self.assertEqual(second.status, 'PLANNED')
        self.assertNotEqual(first.job_id, second.job_id)

    def test_reused_event_identity_holds(self):
        self.route()
        self.assertEqual(self.route(replace(self.event, revision_sha256='b'*64)).status, 'HELD')

    def test_output_feedback_and_unknown_events_ignored(self):
        self.assertEqual(self.route(replace(self.event, origin='OUTPUT')).status, 'IGNORED')
        self.assertEqual(self.route(replace(self.event, kind='OUTPUT_UPDATED')).status, 'IGNORED')

    def test_unenrolled_source_job_and_pause_hold(self):
        self.assertEqual(self.route(replace(self.event, source_id='wrong')).status, 'HELD')
        self.assertEqual(self.route(enrollment=replace(self.enrollment,
            allowed_jobs=('DIAGNOSE_CHECK',))).status, 'HELD')
        self.assertEqual(self.route(enrollment=replace(self.enrollment, paused=True)).status, 'HELD')

    def test_budget_holds_new_work_but_duplicate_remains_visible(self):
        enrollment = replace(self.enrollment, max_jobs=1)
        self.assertEqual(self.route(enrollment=enrollment).status, 'PLANNED')
        self.assertEqual(self.route(enrollment=enrollment).status, 'DUPLICATE')
        self.assertEqual(self.route(replace(self.event, event_id='new', revision_sha256='b'*64),
                                    enrollment).status, 'HELD')

    def test_policy_code_and_authority_changes_bind_new_job(self):
        original = self.route()
        for index, field in enumerate(('policy_revision', 'code_revision', 'authorization_ref')):
            result = self.route(replace(self.event, event_id=str(index)),
                                replace(self.enrollment, **{field: 'synthetic:changed'}))
            self.assertEqual(result.status, 'PLANNED')
            self.assertNotEqual(result.job_id, original.job_id)

    def test_strict_types_and_malformed_input_rejected(self):
        for change in ({'max_jobs': True}, {'max_jobs': 0}, {'paused': 1},
                       {'allowed_jobs': ('RUN_WRITE',)}, {'authorization_ref': ''}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.route(enrollment=replace(self.enrollment, **change))
        with self.assertRaises(ValueError):
            self.route(replace(self.event, revision_sha256='bad'))

    def test_missing_or_reinitialized_storage_not_silently_created(self):
        with self.assertRaises(FileExistsError):
            ObserverQueue(self.path, initialize=True)
        self.path.unlink()
        with self.assertRaises(ValueError):
            ObserverQueue(self.path)
        with self.assertRaises(sqlite3.OperationalError):
            self.route()

    def test_partial_database_not_accepted(self):
        path = Path(self.temp.name) / 'partial.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE unrelated (value TEXT)')
        with self.assertRaises(ValueError):
            ObserverQueue(path)


if __name__ == '__main__':
    unittest.main()
