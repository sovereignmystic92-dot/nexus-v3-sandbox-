"""Bounded SQLite-capacity and outage probes; no live service or credentials."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from nexus_sandbox.cortex_adapter import CortexAdapter, MARKER, Module, Write

SOURCE = 'Nexus Sandbox Recovery Offline Source'
TARGET = 'Nexus Sandbox Recovery Offline Target'
NAMES = frozenset((SOURCE, TARGET))
REVISION = '20735ddade16c47588486252c95d3ffc2192954d'

class CapacityAdapter(CortexAdapter):
    # Test-only subclass: apply a SQLite page ceiling on every new connection.
    # This provokes real SQLITE_FULL, not filesystem ENOSPC or device failure.
    cap_pages = None
    def _db(self):
        db = sqlite3.connect(self.journal)
        db.execute('PRAGMA max_page_count=' + str(self.cap_pages if self.cap_pages is not None else 1048576))
        return db

class Remote:
    def __init__(self):
        self.source = Module('synthetic:source', SOURCE, 1, MARKER + '\nFictional source', ())
        self.modules = {SOURCE: self.source}
        self.writes, self.reads = 0, 0
        self.outage = self.lose_reply = False
        self.after_create = lambda: None
    def get(self, name):
        self.reads += 1
        if self.outage: raise TimeoutError('synthetic read outage')
        return self.modules.get(name)
    def create(self, name, content, dependencies):
        assert name not in self.modules
        self.writes += 1
        self.modules[name] = Module('synthetic:target', name, 1, content, dependencies)
        self.after_create()
        if self.lose_reply: raise TimeoutError('synthetic lost acknowledgment')
    def update(self, *args): raise AssertionError('No update expected')

def snapshot(path):
    with sqlite3.connect(path) as db:
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
        assert integrity == 'ok'
        rows = db.execute('SELECT receipt FROM cortex_receipts').fetchall()
        return {'integrity': integrity, 'receipts': len(rows),
                'events': db.execute('SELECT count(*) FROM cortex_events').fetchone()[0],
                'anchors': db.execute('SELECT count(*) FROM cortex_identity_anchors').fetchone()[0],
                'checkpoints': [json.loads(r[0])['checkpoint'] for r in rows],
                'page_count': db.execute('PRAGMA page_count').fetchone()[0],
                'page_size': db.execute('PRAGMA page_size').fetchone()[0]}

def expect_full(action):
    try: action()
    except sqlite3.OperationalError as exc:
        assert exc.sqlite_errorcode == sqlite3.SQLITE_FULL, str(exc)
        return {'sqlite_errorcode': exc.sqlite_errorcode, 'sqlite_errorname': exc.sqlite_errorname}
    raise AssertionError('Expected SQLITE_FULL')

def run_case(directory, case):
    path = directory / (case + '.sqlite')
    remote = Remote()
    adapter = CapacityAdapter(path, NAMES, remote)
    key = 'synthetic:request:recovery-' + case
    request = Write(key, TARGET, MARKER + '\n' + key + '\n' + ('x' * 60000 if case == 'intent-full' else 'Fictional payload'), (SOURCE,), remote.source)
    observations = {}
    if case == 'intent-full':
        adapter.cap_pages = snapshot(path)['page_count']
        observations['error'] = expect_full(lambda: adapter.ensure(request))
        observations['page_ceiling'] = adapter.cap_pages
        observations['after_failure'] = snapshot(path)
        assert observations['after_failure']['page_count'] <= adapter.cap_pages
        assert remote.writes == 0 and TARGET not in remote.modules
        assert observations['after_failure']['receipts'] == observations['after_failure']['events'] == 0
        observations['writes_before_recovery'] = remote.writes
        adapter.cap_pages = None
        recovered = adapter.ensure(request)
    elif case == 'verification-full':
        with sqlite3.connect(path) as db:
            db.executescript('''CREATE TABLE synthetic_capacity_probe(payload BLOB);
                CREATE TRIGGER fill_on_verification AFTER INSERT ON cortex_events
                WHEN json_extract(NEW.receipt,'$.protocol_verdict')='VERIFIED'
                BEGIN INSERT INTO synthetic_capacity_probe VALUES(zeroblob(65536)); END;''')
        def cap_after_commit(): adapter.cap_pages = snapshot(path)['page_count']
        remote.after_create = cap_after_commit
        observations['error'] = expect_full(lambda: adapter.ensure(request))
        observations['page_ceiling'] = adapter.cap_pages
        observations['after_failure'] = snapshot(path)
        assert observations['after_failure']['page_count'] <= adapter.cap_pages
        assert observations['after_failure']['checkpoints'] == ['WRITE_INTENT']
        assert observations['after_failure']['events'] == 1 and observations['after_failure']['anchors'] == 0
        assert remote.writes == 1 and TARGET in remote.modules
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT count(*) FROM synthetic_capacity_probe').fetchone()[0] == 0
            db.execute('DROP TRIGGER fill_on_verification')
        observations['writes_before_recovery'] = remote.writes
        adapter.cap_pages = None
        recovered = adapter.ensure(request)
        assert recovered.operation_outcome == 'NOT_ATTEMPTED'
    else:
        remote.lose_reply = True
        first = adapter.ensure(request)
        assert first.protocol_verdict == 'UNKNOWN' and remote.writes == 1
        remote.outage = True
        holds = []
        for _ in range(3):
            reopened = CapacityAdapter(path, NAMES, remote)
            hold = reopened.ensure(request)
            assert hold.operation_outcome == 'NOT_ATTEMPTED' and hold.checkpoint == 'READ_BLOCKED'
            assert remote.writes == 1
            holds.append(asdict(hold))
        observations.update(first=asdict(first), read_outage_holds=holds, writes_before_recovery=remote.writes)
        remote.outage = False
        recovered = CapacityAdapter(path, NAMES, remote).ensure(request)
        assert recovered.operation_outcome == 'NOT_ATTEMPTED'
    assert recovered.protocol_verdict == 'VERIFIED' and remote.writes == 1
    observations.update(case=case, assertions='PASSED', recovery=asdict(recovered),
                        total_writes=remote.writes, after_recovery=snapshot(path))
    if adapter.cap_pages is not None: raise AssertionError('Capacity ceiling not released')
    return observations

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='nexus-single-worker-recovery-') as tmp:
        cases = [run_case(Path(tmp), case) for case in ('intent-full','verification-full','uncertain-write-read-outage')]
    report = {'frozen_implementation': REVISION, 'scope': 'Author-run offline single-worker adapter probes',
              'source_sha256': hashlib.sha256((ROOT/'src/nexus_sandbox/cortex_adapter.py').read_bytes()).hexdigest(),
              'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'cases': cases,
              'full_acceptance': 'BLOCKED', 'limits': ['SQLite max_page_count ceiling, not filesystem ENOSPC/device/power loss',
              'Verification capacity fault uses a test-only event trigger',
              'In-memory remote and deliberate timeout, not live network failures',
              'Adapter reopenings in one Python process, not process/host restart',
              'No multiworker exclusivity, permissions isolation or human review established']}
    encoded=json.dumps(report,indent=2)+'\n'
    if args.output: args.output.write_text(encoded)
    else: print(encoded,end='')
    print(json.dumps({'cases':len(cases),'assertions':'PASSED','full_acceptance':'BLOCKED'}),file=sys.stderr)
if __name__ == '__main__': main()
