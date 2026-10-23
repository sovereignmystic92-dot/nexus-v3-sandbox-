"""Offline counterexample/control for C9; does not invoke Cortex or prove fencing."""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from nexus_sandbox.cortex_adapter import CortexAdapter, MARKER, Module, Write

SOURCE = 'Nexus Sandbox C9 Offline Source'
TARGET = 'Nexus Sandbox C9 Offline Target'
NAMES = frozenset((SOURCE, TARGET))
FROZEN_REVISION = 'ac954ff9759771d48020ba4700797841b7968d3d'


def run_case(shared_journal, same_request=False):
    source = Module('synthetic:source', SOURCE, 1, MARKER + '\nFictional source', ())
    baseline = Module('synthetic:target', TARGET, 1, MARKER + '\nFictional baseline', (SOURCE,))
    state = {SOURCE: source, TARGET: baseline}
    lock = threading.Lock()
    entered = threading.Event()
    release = threading.Event()
    trace, outcomes, errors = [], {}, []

    class Transport:
        def __init__(self, worker): self.worker = worker
        def get(self, name):
            with lock:
                item = state[name]
                trace.append({'worker': self.worker, 'action': 'read', 'name': name, 'version': item.version})
                return item
        def create(self, *args): raise AssertionError('No create expected')
        def update(self, name, content, dependencies):
            if self.worker == 'A':
                entered.set()
                if not release.wait(5): raise TimeoutError('Bounded synthetic pause expired')
            with lock:
                old = state[name]
                state[name] = replace(old, version=old.version + 1, content=content, dependencies=dependencies)
                trace.append({'worker': self.worker, 'action': 'update', 'from_version': old.version,
                              'to_version': state[name].version})

    with tempfile.TemporaryDirectory(prefix='nexus-c9-offline-') as temporary:
        paths = [Path(temporary) / 'A.sqlite', Path(temporary) / ('A.sqlite' if shared_journal else 'B.sqlite')]
        key_a = 'synthetic:request:c9-worker-A'
        key_b = key_a if same_request else 'synthetic:request:c9-worker-B'
        request_a = Write(key_a, TARGET, MARKER + '\n' + key_a + '\nPayload A', (SOURCE,), source, baseline)
        request_b = request_a if same_request else replace(request_a, key=key_b, content=MARKER + '\n' + key_b + '\nPayload B')
        adapters = [CortexAdapter(paths[i], NAMES, Transport(worker)) for i, worker in enumerate(('A', 'B'))]
        def worker_a():
            try: outcomes['A'] = asdict(adapters[0].ensure(request_a))
            except BaseException as exc: errors.append(type(exc).__name__ + ': ' + str(exc))
        thread = threading.Thread(target=worker_a, daemon=True)
        thread.start()
        try:
            assert entered.wait(5), 'A did not reach its update boundary'
            outcomes['B'] = asdict(adapters[1].ensure(request_b))
            after_b = state[TARGET]
        finally:
            release.set()
            thread.join(5)
        assert not thread.is_alive(), 'Worker failed to terminate within bound'
        assert not errors, errors
        writes = [entry for entry in trace if entry['action'] == 'update']
        assert state[SOURCE] == source
        assert state[TARGET].id == baseline.id
        if same_request:
            assert outcomes['B']['checkpoint'] == 'RECONCILE_ONLY'
            assert outcomes['B']['operation_outcome'] == 'NOT_ATTEMPTED'
            assert outcomes['A']['protocol_verdict'] == 'VERIFIED'
            assert len(writes) == 1 and state[TARGET].version == 2
            meaning = 'Same-key shared-journal durable intent prevented a second write in this interleaving'
        else:
            assert outcomes['B']['protocol_verdict'] == 'VERIFIED'
            assert after_b.version == 2 and after_b.content == request_b.content
            assert [entry['worker'] for entry in writes] == ['B', 'A']
            assert outcomes['A']['operation_outcome'] == 'SUCCEEDED'
            assert outcomes['A']['protocol_verdict'] == 'FAILED'
            assert outcomes['A']['checkpoint'] == 'READBACK_MISMATCH'
            assert state[TARGET].version == 3 and state[TARGET].content == request_a.content
            meaning = 'A passed v1 preflight, then overwrote B v2; readback detected v3 only after the stale write'
        journals = []
        for path in sorted(set(paths)):
            with sqlite3.connect(path) as db:
                integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
                assert integrity == 'ok'
                journals.append({'journal': path.name, 'integrity': integrity,
                                 'receipt_count': db.execute('SELECT count(*) FROM cortex_receipts').fetchone()[0]})
        return {'case': ('same-request-shared-journal' if same_request else
                         'different-requests-' + ('shared' if shared_journal else 'separate') + '-journals'),
                'assertions': 'PASSED', 'demonstrates_unfenced_write': not same_request,
                'meaning': meaning, 'outcomes': outcomes, 'final_target': asdict(state[TARGET]),
                'writes': len(writes), 'trace': trace, 'journals': journals}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    cases = [run_case(False), run_case(True), run_case(True, True)]
    report = {'scope': 'Author-run deterministic offline thread interleavings with an in-memory transport',
              'frozen_implementation': FROZEN_REVISION,
              'source_sha256': hashlib.sha256((ROOT / 'src/nexus_sandbox/cortex_adapter.py').read_bytes()).hexdigest(),
              'probe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'cases': cases, 'c9_acceptance': 'BLOCKED',
              'limits': ['No live calls, real server race, process/host lease or fencing implementation',
                         'Passing counterexample assertions demonstrate a missing guarantee, not concurrency safety',
                         'The same-key control is one schedule, not a proof for all overlapping invocations']}
    encoded = json.dumps(report, indent=2) + '\n'
    if args.output: args.output.write_text(encoded)
    else: print(encoded, end='')
    print(json.dumps({'cases': len(cases), 'assertions': 'PASSED', 'c9_acceptance': 'BLOCKED'}), file=sys.stderr)

if __name__ == '__main__': main()
