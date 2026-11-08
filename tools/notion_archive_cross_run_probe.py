"""Manual synthetic cross-run checkpoint handoff. No automatic triggers."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notion_archive_live_probe as live

SCHEMA = 'nexus.synthetic-archive-checkpoint.v1'
STATES = {'READBACK_REQUIRED', 'MISSING_CHUNKS', 'WRITE_INTENT',
          'WRITE_OUTCOME_UNKNOWN', 'BLOCKED_AUTHORIZATION',
          'BLOCKED_UNCERTAIN_WRITE', 'ARCHIVE_VERIFIED'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def binding(prepared, destination):
    return json.dumps({'destination': destination, 'prepared': prepared,
                       'source_sha256': prepared['receipt']['sha256']}, sort_keys=True)


def export_checkpoint(path, prepared, destination, journal_destination, run_id, revision):
    with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as db:
        actual = db.execute('SELECT singleton,binding FROM archive_binding').fetchall()
        if actual != [(1, binding(prepared, destination))]:
            raise ValueError('local journal binding mismatch')
        events = [list(row) for row in db.execute(
            'SELECT id,state,chunk_index FROM archive_events ORDER BY id')]
    return {'schema': SCHEMA, 'destination': destination,
            'journal_destination': journal_destination,
            'source_sha256': prepared['receipt']['sha256'],
            'origin_run_id': run_id, 'code_revision': revision, 'events': events}


def validate_checkpoint(value, expected_hash, prepared, destination, journal_destination,
                        run_id, revision, *, require_other_run):
    if (not isinstance(value, dict) or set(value) != {'schema', 'destination',
            'journal_destination', 'source_sha256', 'origin_run_id', 'code_revision', 'events'}
            or digest(value) != expected_hash or value['schema'] != SCHEMA
            or value['destination'] != destination
            or value['journal_destination'] != journal_destination
            or value['source_sha256'] != prepared['receipt']['sha256']
            or value['code_revision'] != revision
            or not isinstance(value['origin_run_id'], str)
            or not value['origin_run_id'].isdigit()
            or (require_other_run and value['origin_run_id'] == run_id)):
        raise ValueError('checkpoint identity/hash mismatch')
    events = value['events']
    if not isinstance(events, list) or not 1 <= len(events) <= 100:
        raise ValueError('checkpoint event bound')
    for i, row in enumerate(events, 1):
        if (not isinstance(row, list) or len(row) != 3 or type(row[0]) is not int
                or row[0] != i or row[1] not in STATES
                or (row[2] is not None and (type(row[2]) is not int
                    or not 0 <= row[2] < len(prepared['chunks'])))):
            raise ValueError('invalid journal history')
    # Only the exact one-write paused prefix is portable in this test protocol.
    if events != [[1, 'READBACK_REQUIRED', None], [2, 'MISSING_CHUNKS', None],
                  [3, 'WRITE_INTENT', 0], [4, 'READBACK_REQUIRED', None],
                  [5, 'MISSING_CHUNKS', None]]:
        raise ValueError('unexpected paused journal history')
    return value


def restore_checkpoint(path, value, prepared, destination):
    # No overwrite, migration, SQLite binary import or caller-supplied SQL.
    path = Path(path)
    with path.open('xb'):
        pass
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE archive_binding (singleton INTEGER PRIMARY KEY CHECK(singleton=1), binding TEXT NOT NULL)')
        db.execute('CREATE TABLE archive_events (id INTEGER PRIMARY KEY, state TEXT NOT NULL, chunk_index INTEGER)')
        db.execute('INSERT INTO archive_binding VALUES (1,?)', (binding(prepared, destination),))
        db.executemany('INSERT INTO archive_events VALUES (?,?,?)', value['events'])


def rich_text(parts):
    return live.NotionArchivePort._text(parts)


def read_checkpoint(client, destination):
    page = client.list(block_id=destination, page_size=100)
    if (not isinstance(page, dict) or page.get('has_more') is not False
            or not isinstance(page.get('results'), list) or len(page['results']) > 1):
        raise ValueError('journal page must contain at most one checkpoint block')
    if not page['results']:
        return None
    block = page['results'][0]
    if (block.get('type') != 'code' or block.get('has_children') is not False
            or block.get('archived') or block.get('in_trash')):
        raise ValueError('invalid checkpoint block')
    parent = block.get('parent', {})
    if str(UUID(parent.get(parent.get('type')))) != destination:
        raise ValueError('wrong checkpoint container')
    code = block['code']
    if rich_text(code.get('caption')) != SCHEMA:
        raise ValueError('foreign checkpoint block')
    raw = rich_text(code.get('rich_text'))
    if len(raw.encode('utf-8')) > 16384:
        raise ValueError('checkpoint too large')
    value = json.loads(raw)
    if raw != canonical(value):
        raise ValueError('noncanonical checkpoint')
    return value


def save_checkpoint(client, destination, value):
    raw = canonical(value)
    if len(raw.encode('utf-8')) > 16384 or read_checkpoint(client, destination) is not None:
        raise ValueError('checkpoint destination is not empty')
    def rich(text):
        return [{'type': 'text', 'text': {'content': text[i:i+1000]}}
                for i in range(0, len(text), 1000)]
    # One immutable append; a failed/uncertain result is never retried here.
    client.append(block_id=destination, position={'type': 'end'}, children=[{
        'object': 'block', 'type': 'code', 'code': {'language': 'json',
            'caption': rich(SCHEMA), 'rich_text': rich(raw)}}])
    if read_checkpoint(client, destination) != value:
        raise ValueError('checkpoint readback mismatch')


def probe(phase, destination, journal_destination, expected_hash, run_id, revision,
          local_path, client_factory, *, allow_write):
    if phase not in {'pause', 'resume', 'observe'}:
        raise ValueError('invalid phase')
    if (str(UUID(destination)) != destination
            or str(UUID(journal_destination)) != journal_destination
            or destination == journal_destination):
        raise ValueError('two distinct canonical fixture IDs required')
    prepared = live.prepare_transcript(live.RAW, 256)
    sha = prepared['receipt']['sha256']
    journal = client_factory(journal_destination, allow_write and phase == 'pause')
    snapshot = read_checkpoint(journal, journal_destination)
    writes = 0
    if phase == 'pause' and allow_write:
        if snapshot is not None:
            raise ValueError('pause requires a new empty journal')
        client = client_factory(destination, True)
        port = live.NotionArchivePort(client, prepared, destination, expected_source_sha256=sha)
        if port.read_archive(destination, sha)['chunks']:
            raise ValueError('pause requires a new empty archive')
        result = live.ArchiveRecoveryHost(local_path).attempt(
            prepared, destination, expected_source_sha256=sha,
            read_archive=port.read_archive, write_chunk=port.write_chunk,
            authorize_write=lambda d, s, i: d == destination and s == sha and i == 0)
        if result['state'] != 'MISSING_CHUNKS' or client.writes != 1:
            raise ValueError('expected one-chunk pause')
        snapshot = export_checkpoint(local_path, prepared, destination, journal_destination, run_id, revision)
        expected_hash = digest(snapshot)
        validate_checkpoint(snapshot, expected_hash, prepared, destination, journal_destination,
                            run_id, revision, require_other_run=False)
        save_checkpoint(journal, journal_destination, snapshot)
        return {'result': 'PAUSED_CHECKPOINT_VERIFIED', 'checkpoint_sha256': expected_hash,
                'archive_writes': 1, 'checkpoint_writes': 1, 'archive_state': result['state'],
                'origin_run_id': run_id, 'audit_promotion': False, 'unattended_readiness': False}
    if snapshot is None or not expected_hash:
        raise ValueError('pinned remote checkpoint required')
    validate_checkpoint(snapshot, expected_hash, prepared, destination, journal_destination,
                        run_id, revision, require_other_run=(phase == 'resume'))
    if phase == 'resume' and allow_write:
        restore_checkpoint(local_path, snapshot, prepared, destination)
        for _ in range(len(prepared['chunks']) - 1):
            client = client_factory(destination, True)
            port = live.NotionArchivePort(client, prepared, destination, expected_source_sha256=sha)
            result = live.ArchiveRecoveryHost(local_path).attempt(
                prepared, destination, expected_source_sha256=sha,
                read_archive=port.read_archive, write_chunk=port.write_chunk,
                authorize_write=lambda d, s, i: d == destination and s == sha and i > 0)
            writes += client.writes
    client = client_factory(destination, False)
    port = live.NotionArchivePort(client, prepared, destination, expected_source_sha256=sha)
    from nexus_sandbox.transcript_ingestion_gate import plan_archive_resume
    result = plan_archive_resume(prepared, destination, port.read_archive(destination, sha),
                                 expected_source_sha256=sha)
    if phase != 'pause' and result['state'] != 'ARCHIVE_VERIFIED':
        raise ValueError('archive incomplete; no blind retry')
    return {'result': ('VERIFIED' if result['state'] == 'ARCHIVE_VERIFIED' else 'PAUSED_OBSERVED'),
            'checkpoint_sha256': expected_hash, 'origin_run_id': snapshot['origin_run_id'],
            'current_run_id': run_id, 'archive_state': result['state'],
            'archive_writes': writes, 'checkpoint_writes': 0,
            'audit_promotion': False, 'unattended_readiness': False}


def main():
    phase = os.environ.get('NOTION_ARCHIVE_CROSS_RUN_PHASE', 'disabled')
    if phase == 'disabled':
        return live.main()
    if (os.environ.get('GITHUB_REPOSITORY') != 'sovereignmystic92-dot/nexus-v3-sandbox-'
            or os.environ.get('GITHUB_REF') != 'refs/heads/main'
            or os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
            or os.environ.get('NOTION_ARCHIVE_TEST_CONFIRMED') != 'true'
            or os.environ.get('NOTION_ARCHIVE_LOST_REPLY_CONFIRMED') == 'true'):
        print('{"result":"BLOCKED_CONFIGURATION"}')
        return 2
    try:
        run_id, revision = os.environ['GITHUB_RUN_ID'], os.environ['GITHUB_SHA']
        if not run_id.isdigit() or len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision):
            raise ValueError('invalid execution identity')
        first_attempt = os.environ.get('GITHUB_RUN_ATTEMPT') == '1'
        def factory(destination, write):
            return live.BoundClient(destination, os.environ.get('NOTION_SANDBOX_TOKEN', ''),
                                    write and first_attempt)
        summary = probe(phase, os.environ['NOTION_ARCHIVE_FIXTURE_ID'],
            os.environ['NOTION_ARCHIVE_JOURNAL_ID'], os.environ.get('NOTION_ARCHIVE_CHECKPOINT_SHA256', ''),
            run_id, revision, str(Path(os.environ['RUNNER_TEMP']) / 'archive-probe.sqlite'),
            factory, allow_write=first_attempt)
        print(json.dumps(summary, sort_keys=True))
        return 0
    except Exception:
        print('{"result":"BLOCKED","next":"OBSERVE_ONLY_NO_BLIND_RETRY"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
