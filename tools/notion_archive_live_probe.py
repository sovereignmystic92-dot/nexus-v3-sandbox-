"""Manual synthetic-source live probe; no schedule, real transcripts or SDK install."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import urllib.parse
import urllib.request
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nexus_sandbox.transcript_ingestion_gate import (
    ArchiveRecoveryHost, NotionArchivePort, prepare_transcript)

RAW = ('NEXUS SYNTHETIC ARCHIVE PROBE >> [music]  \n' * 15)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('redirect refused')


class BoundClient:
    """Minimal SDK shape; one fixed HTTPS origin/page, no automatic retries."""
    def __init__(self, destination, token, allow_write):
        if str(UUID(destination)) != destination or not token or '\n' in token or '\r' in token:
            raise ValueError('explicit configuration required')
        self.destination, self.token = destination, token
        self.allow_write, self.writes = allow_write, 0
        self.opener = urllib.request.build_opener(NoRedirect())
        self.blocks = SimpleNamespace(children=SimpleNamespace(list=self.list, append=self.append))

    def request(self, method, path, payload=None):
        prefix = '/v1/blocks/' + self.destination + '/children'
        if method == 'GET':
            if not path.startswith(prefix + '?') or payload is not None:
                raise ValueError('unbound read')
        elif method == 'PATCH':
            if path != prefix or self.allow_write is not True or self.writes:
                raise ValueError('unbound or exhausted write')
            self.writes += 1  # Count uncertain requests before network access.
        else:
            raise ValueError('method refused')
        data = None if payload is None else json.dumps(payload, allow_nan=False).encode('utf-8')
        req = urllib.request.Request('https://api.notion.com' + path, data=data,
            method=method, headers={'Authorization': 'Bearer ' + self.token,
            'Notion-Version': '2025-09-03', 'Content-Type': 'application/json'})
        try:
            with self.opener.open(req, timeout=20) as response:
                raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    raise ValueError('response bound exceeded')
                result = json.loads(raw)
                if not isinstance(result, dict) or result.get('object') == 'error':
                    raise ValueError('invalid response')
                return result
        except Exception:
            raise RuntimeError('provider request unavailable; reconcile before retry') from None

    def list(self, *, block_id, page_size, start_cursor=None):
        if block_id != self.destination or page_size != 100:
            raise ValueError('unbound listing')
        query = {'page_size': 100}
        if start_cursor is not None:
            query['start_cursor'] = start_cursor
        return self.request('GET', '/v1/blocks/' + block_id + '/children?' + urllib.parse.urlencode(query))

    def append(self, *, block_id, children, position):
        if block_id != self.destination or len(children) != 1:
            raise ValueError('one bound block required')
        return self.request('PATCH', '/v1/blocks/' + block_id + '/children',
                            {'children': children, 'position': position})


def child(destination, journal, allow_write, *, discard_reply=False):
    prepared = prepare_transcript(RAW, 256)
    sha = prepared['receipt']['sha256']
    client = BoundClient(destination, os.environ.get('NOTION_SANDBOX_TOKEN', ''), allow_write)
    port = NotionArchivePort(client, prepared, destination, expected_source_sha256=sha)
    def write_with_fault(*args):
        port.write_chunk(*args)
        if discard_reply:
            if client.writes != 1:
                raise ValueError('fault requires one new committed request')
            # The HTTP response arrived, but the host never records an ACK or
            # conducts post-write readback. This is not a network timeout.
            os.write(1, json.dumps({'fault': 'ACK_DISCARDED_AFTER_SUCCESS',
                                   'writes': 1}).encode('utf-8'))
            import signal
            os.kill(os.getpid(), signal.SIGKILL)
    if discard_reply and not allow_write:
        raise ValueError('fault requires explicit write mode')
    if allow_write:
        result = ArchiveRecoveryHost(journal).attempt(
            prepared, destination, expected_source_sha256=sha,
            read_archive=port.read_archive, write_chunk=write_with_fault,
            authorize_write=lambda dest, source, index: dest == destination and source == sha)
    else:
        from nexus_sandbox.transcript_ingestion_gate import plan_archive_resume
        result = plan_archive_resume(prepared, destination, port.read_archive(destination, sha),
                                     expected_source_sha256=sha)
    # Fixed summary only: no token, provider errors, response bodies or raw payloads.
    return {'state': result['state'], 'writes': client.writes, 'source_sha256': sha,
            'destination': destination, 'audit_promotion': False}


def main():
    if (os.environ.get('GITHUB_REPOSITORY') != 'sovereignmystic92-dot/nexus-v3-sandbox-'
            or os.environ.get('GITHUB_REF') != 'refs/heads/main'
            or os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
            or os.environ.get('NOTION_ARCHIVE_TEST_CONFIRMED') != 'true'):
        print('{"result":"BLOCKED_CONFIGURATION"}')
        return 2
    try:
        destination = os.environ['NOTION_ARCHIVE_FIXTURE_ID']
        if str(UUID(destination)) != destination:
            raise ValueError('canonical fixture required')
        if len(sys.argv) == 3 and sys.argv[1] == '--child':
            write = sys.argv[2] in ('write', 'lost-reply') and os.environ.get('GITHUB_RUN_ATTEMPT') == '1'
            result = child(destination, str(Path(os.environ['RUNNER_TEMP']) / 'archive-probe.sqlite'), write,
                           discard_reply=(sys.argv[2] == 'lost-reply' and write
                               and os.environ.get('NOTION_ARCHIVE_LOST_REPLY_CONFIRMED') == 'true'))
            print(json.dumps(result, sort_keys=True))
            return 0
        # Each iteration is a fresh process reopening the same journal. On a
        # workflow rerun, all children are strictly observe-only, even if absent.
        n = len(prepare_transcript(RAW, 256)['chunks'])
        mode = 'write' if os.environ.get('GITHUB_RUN_ATTEMPT') == '1' else 'observe'
        fault_enabled = (mode == 'write'
            and os.environ.get('NOTION_ARCHIVE_LOST_REPLY_CONFIRMED') == 'true')
        summaries = []
        for iteration in range(n):
            child_mode = 'lost-reply' if fault_enabled and iteration == 0 else mode
            proc = subprocess.run([sys.executable, '-I', __file__, '--child', child_mode],
                capture_output=True, text=True, timeout=150)
            if child_mode == 'lost-reply':
                import signal
                if (proc.returncode != -signal.SIGKILL or json.loads(proc.stdout) !=
                        {'fault': 'ACK_DISCARDED_AFTER_SUCCESS', 'writes': 1}):
                    raise ValueError('expected controlled fault not observed')
            elif proc.returncode != 0:
                raise ValueError('child failed; reconcile before retry')
            summaries.append(json.loads(proc.stdout))
        proc = subprocess.run([sys.executable, '-I', __file__, '--child', 'observe'],
            capture_output=True, text=True, timeout=150, check=True)
        final = json.loads(proc.stdout)
        if final['state'] != 'ARCHIVE_VERIFIED' or final['writes'] != 0:
            raise ValueError('final readback incomplete')
        print(json.dumps({'result': 'VERIFIED', 'processes': n + 1,
            'writes_attempted': sum(s['writes'] for s in summaries),
            'final': final, 'scope': ('LIVE_SYNTHETIC_POST_ACK_SIGKILL_RECOVERY' if fault_enabled
                      else 'LIVE_SYNTHETIC_SAME_RUN_PROCESS_REOPEN'),
            'controlled_fault_observed': fault_enabled,
            'unattended_readiness': False}, sort_keys=True))
        return 0
    except Exception:
        print('{"result":"BLOCKED","next":"OBSERVE_ONLY_NO_BLIND_RETRY"}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
