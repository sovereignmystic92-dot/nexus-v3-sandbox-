"""Transactional local CI observation history; no scheduler or repair executor."""
import json
import sqlite3

from failure_handoff import collect, require


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


class FailureStore:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=5, isolation_level=None)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS observations ('
                        'seq INTEGER PRIMARY KEY, repository TEXT NOT NULL, '
                        'run_id INTEGER NOT NULL, attempt INTEGER NOT NULL, payload TEXT NOT NULL, '
                        'UNIQUE(repository, run_id, attempt, payload))')

    def close(self):
        self.db.close()

    def _latest(self, repo):
        rows = self.db.execute('SELECT payload FROM observations WHERE repository=? ORDER BY seq', (repo,))
        latest = {}
        for (payload,) in rows:
            report = json.loads(payload)
            collect(dict(repository=repo, current_sha=report['source_sha'], reports=[report]))
            latest[(report['run_id'], report['attempt'])] = report
        return latest

    @staticmethod
    def _view(repo, sha, latest):
        # Classify each run independently to preserve the collector's 100-attempt
        # bound without silently truncating the repository's other run history.
        groups = {}
        for report in latest.values():
            groups.setdefault(report['run_id'], []).append(report)
        findings = {}; runs = []
        for run_id in sorted(groups):
            result = collect(dict(repository=repo, current_sha=sha, reports=groups[run_id]))
            runs.extend(result['runs'])
            for finding in result['findings']:
                key = finding['finding_id']
                if key in findings:
                    findings[key]['observations'].extend(finding['observations'])
                else:
                    findings[key] = finding
        return dict(repository=repo, current_sha=sha, runs=runs,
                    findings=[findings[k] for k in sorted(findings)])

    def ingest(self, packet):
        # Validate before opening the write transaction. Evidence authenticity is
        # still the retrieval adapter's responsibility.
        collect(packet)
        repo, sha = packet['repository'], packet['current_sha']
        self.db.execute('BEGIN IMMEDIATE')
        try:
            latest = self._latest(repo)
            before = self._view(repo, sha, latest)
            inserted = 0
            for report in packet['reports']:
                key = (report['run_id'], report['attempt'])
                if self.db.execute('SELECT 1 FROM observations WHERE repository=? AND '
                                   'run_id=? AND attempt=? AND payload=?',
                                   (repo, key[0], key[1], encode(report))).fetchone():
                    continue
                old = latest.get(key)
                if old is not None and old != report:
                    require(old['source_sha'] == report['source_sha'])
                    # Completed results are immutable except for filling in an
                    # entirely absent case list with matching metadata.
                    if old['status'] == 'completed':
                        require(not old['cases'] and bool(report['cases']))
                        require({k:v for k,v in old.items() if k != 'cases'} ==
                                {k:v for k,v in report.items() if k != 'cases'})
                    else:
                        rank = {'queued':0, 'pending':0, 'in_progress':1, 'completed':2}
                        require(rank[report['status']] >= rank[old['status']])
                cursor = self.db.execute('INSERT OR IGNORE INTO observations '
                    '(repository,run_id,attempt,payload) VALUES (?,?,?,?)',
                    (repo, key[0], key[1], encode(report)))
                inserted += cursor.rowcount
                latest[key] = report
            after = self._view(repo, sha, latest)
            prior = {f['finding_id'] for f in before['findings']}
            active = {f['finding_id'] for f in after['findings']}
            result = dict(after, observations_inserted=inserted,
                          newly_active_findings=[f for f in after['findings'] if f['finding_id'] not in prior],
                          inactive_finding_ids=sorted(prior-active), repair_applied=False)
            self.db.execute('COMMIT')
            return result
        except BaseException:
            self.db.execute('ROLLBACK')
            raise
