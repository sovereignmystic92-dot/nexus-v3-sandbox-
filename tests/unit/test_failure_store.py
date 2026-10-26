from copy import deepcopy
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from failure_store import FailureStore
from failure_handoff import InvalidEvidence


class FailureStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'findings.db')
        self.store = FailureStore(self.path)
        self.report = dict(repository='test/repo', run_id=1, attempt=1, source_sha='a'*40,
            status='completed', conclusion='failure', cases=[dict(test_id='suite.test',
            status='FAILED', failure_signature='b'*64)])
    def tearDown(self):
        self.store.close(); self.tmp.cleanup()
    def packet(self, *reports, sha=None):
        return dict(repository='test/repo', current_sha=sha or 'a'*40, reports=list(reports))
    def success(self):
        report=deepcopy(self.report); report.update(attempt=2, conclusion='success')
        report['cases'][0].update(status='PASSED', failure_signature=None)
        return report
    def test_restart_and_duplicate_delivery_keep_one_finding(self):
        first=self.store.ingest(self.packet(self.report))
        self.assertEqual(len(first['newly_active_findings']),1)
        self.store.close(); self.store=FailureStore(self.path)
        repeat=self.store.ingest(self.packet(self.report))
        self.assertEqual(repeat['observations_inserted'],0)
        self.assertEqual(repeat['newly_active_findings'],[])
        self.assertEqual(len(repeat['findings']),1)
    def test_success_retains_history_and_old_attempt_does_not_revive(self):
        self.store.ingest(self.packet(self.report))
        result=self.store.ingest(self.packet(self.success()))
        self.assertEqual(result['findings'],[])
        self.assertEqual(len(result['inactive_finding_ids']),1)
        self.assertEqual(self.store.ingest(self.packet(self.report))['findings'],[])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM observations').fetchone()[0],2)
    def test_same_finding_across_runs_has_two_observations(self):
        self.store.ingest(self.packet(self.report))
        other=dict(self.report,run_id=2)
        result=self.store.ingest(self.packet(other))
        self.assertEqual(len(result['findings']),1)
        self.assertEqual(len(result['findings'][0]['observations']),2)
        self.assertEqual(result['newly_active_findings'],[])
    def test_conflict_rolls_back_whole_batch(self):
        self.store.ingest(self.packet(self.report))
        conflict=dict(self.report,conclusion='cancelled')
        with self.assertRaises(InvalidEvidence):
            self.store.ingest(self.packet(dict(self.report,run_id=2),conflict))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM observations').fetchone()[0],1)
    def test_pending_to_completed_and_old_snapshot_replay(self):
        pending=dict(self.report,status='in_progress',conclusion=None,cases=[])
        self.store.ingest(self.packet(pending))
        self.assertEqual(len(self.store.ingest(self.packet(self.report))['findings']),1)
        self.assertEqual(len(self.store.ingest(self.packet(pending))['findings']),1)
    def test_missing_cases_can_be_enriched_but_never_removed(self):
        missing=dict(self.report,cases=[])
        self.store.ingest(self.packet(missing))
        self.assertEqual(len(self.store.ingest(self.packet(self.report))['findings']),1)
        self.assertEqual(len(self.store.ingest(self.packet(missing))['findings']),1)
    def test_stale_revision_is_not_current_work(self):
        self.store.ingest(self.packet(self.report))
        result=self.store.ingest(self.packet(sha='c'*40))
        self.assertEqual(result['findings'],[])
        self.assertEqual(result['runs'][0]['disposition'],'STALE_REVISION')
    def test_sqlite_failure_leaves_no_partial_observation(self):
        self.store.db.execute("CREATE TRIGGER refuse BEFORE INSERT ON observations BEGIN SELECT RAISE(ABORT,'injected'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.store.ingest(self.packet(self.report))
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM observations').fetchone()[0],0)
    def test_fresh_process_sees_success_and_no_duplicate_work(self):
        self.store.ingest(self.packet(self.report,self.success()))
        script="import sys; from failure_store import FailureStore; s=FailureStore(sys.argv[1]); r=s.ingest({'repository':'test/repo','current_sha':'a'*40,'reports':[]}); assert not r['findings']; assert r['runs'][0]['prior_failed_case_count']==1; s.close()"
        result=subprocess.run([sys.executable,'-c',script,self.path],env=__import__('os').environ | {'PYTHONPATH':str(Path(__file__).resolve().parents[2]/'tools')},capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
