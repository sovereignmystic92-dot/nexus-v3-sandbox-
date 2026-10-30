"""Opt-in transcript five-pass promotion ledger; never grants deployment authority.

The caller must supply independently reviewed evidence, sourced from a trusted
completion/readback host. Local SQLite cannot prove remote custody or CP09.
No listener, provider API, automatic promotion or execution is installed.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3

from .event_router import ObserverQueue

REQUIRED = frozenset({'job_id', 'source_id', 'revision_sha256',
                      'policy_revision', 'code_revision', 'authorization_ref',
                      'result', 'evidence_id', 'verified_readback'})
RESULTS = frozenset({'VERIFIED_SUCCESS', 'FAILED', 'INCONCLUSIVE', 'INTERRUPTED'})


@dataclass(frozen=True)
class PromotionDecision:
    status: str
    consecutive: int
    next_action: str


class FivePassLedger:
    """Local cooperating-worker ledger; no authority to promote capabilities."""
    def __init__(self, path, *, initialize=False):
        self.path = Path(path)
        if self.path.is_symlink():
            raise ValueError('Symlink not supported')
        if initialize:
            with self.path.open('xb'):
                pass
        if not self.path.is_file():
            raise ValueError('Missing ledger; do not silently reset history')
        with self._connect() as db:
            if initialize:
                db.execute('CREATE TABLE records (seq INTEGER PRIMARY KEY AUTOINCREMENT, '
                           'job_id TEXT UNIQUE NOT NULL, fingerprint TEXT NOT NULL, '
                           'configuration TEXT NOT NULL, outcome TEXT NOT NULL)')
            elif 'records' not in {r[0] for r in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}:
                raise ValueError('Invalid ledger')

    def _connect(self):
        return sqlite3.connect(self.path.resolve().as_uri()+'?mode=rw', uri=True)

    def record(self, evidence, *, observer_queue: ObserverQueue):
        """Count only uniquely identified completed transcript jobs.

        The observer queue proves a matching locally planned binding, *not*
        authenticity of the evidence. The host must verify the completion,
        full transcript, output, registration and readback independently.
        """
        if (type(evidence) is not dict or set(evidence) != REQUIRED
                or any(type(v) is not str or not v or len(v) > 512
                       for k,v in evidence.items() if k != 'verified_readback')
                or type(evidence['verified_readback']) is not bool
                or evidence['result'] not in RESULTS):
            raise ValueError('Invalid completion evidence')
        with observer_queue.connect() as queue:
            row = queue.execute('SELECT binding FROM jobs WHERE job_id=?',
                                (evidence['job_id'],)).fetchone()
        if row is None:
            return PromotionDecision('BLOCKED', 0, 'VERIFY_ENROLLED_TRANSCRIPT_JOB')
        binding = json.loads(row[0])
        if (binding.get('action') != 'INSPECT_TRANSCRIPT'
                or any(binding.get(k) != evidence[k] for k in
                       ('source_id', 'policy_revision', 'code_revision', 'authorization_ref'))
                or binding.get('revision_sha256') != evidence['revision_sha256']):
            return PromotionDecision('BLOCKED', 0, 'RECONCILE_JOB_BINDING')
        if evidence['result'] == 'VERIFIED_SUCCESS' and not evidence['verified_readback']:
            return PromotionDecision('BLOCKED', 0, 'VERIFY_COMPLETION_READBACK')
        configuration = json.dumps([evidence['policy_revision'], evidence['code_revision'],
                                    evidence['authorization_ref']], separators=(',', ':'))
        fingerprint = json.dumps(evidence, sort_keys=True, separators=(',', ':'))
        with self._connect() as db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT fingerprint FROM records WHERE job_id=?',
                               (evidence['job_id'],)).fetchone()
            if prior is not None:
                if prior[0] != fingerprint:
                    return PromotionDecision('BLOCKED', 0, 'RECONCILE_CONFLICTING_EVIDENCE')
                return PromotionDecision('DUPLICATE', self._streak(db, configuration),
                                         'NO_ACTION')
            db.execute('INSERT INTO records (job_id,fingerprint,configuration,outcome) '
                       'VALUES (?,?,?,?)', (evidence['job_id'], fingerprint,
                                            configuration,evidence['result']))
            count = self._streak(db, configuration)
            if evidence['result'] == 'VERIFIED_SUCCESS':
                return PromotionDecision('REVIEW_ELIGIBLE' if count >= 5 else 'OBSERVING',
                                         count, 'REQUEST_INDEPENDENT_PROMOTION_REVIEW'
                                         if count >= 5 else 'AWAIT_NEXT_DISTINCT_VERIFIED_JOB')
            return PromotionDecision('STREAK_RESET' if evidence['result'] == 'FAILED'
                                     else 'HELD_UNCERTAIN',count,
                                     'DIAGNOSE_FAILURE' if evidence['result'] == 'FAILED'
                                     else 'RECONCILE_PENDING_RESULT')

    @staticmethod
    def _streak(db, configuration):
        count = 0
        for conf, outcome in db.execute(
                'SELECT configuration,outcome FROM records ORDER BY seq DESC'):
            if conf != configuration or outcome != 'VERIFIED_SUCCESS':
                break
            count += 1
        return min(count, 5)
