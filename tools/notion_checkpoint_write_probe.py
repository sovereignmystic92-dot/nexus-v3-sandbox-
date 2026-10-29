"""Manual one-checkpoint Actions probe; no workflow/service activation."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nexus_sandbox.audit_checkpoint_transport import AuditCheckpointTransport, canonical
from nexus_sandbox.checkpoint_json import encode
from nexus_sandbox.notion_checkpoint_api import NotionCheckpointAPI, NotionRequest

AUDIT_ID = '4018c067daa48122b82ec2ae8067d021'
POLICY = 'bounded-live-checkpoint-test-20261028-v1'


def probe(request, run_id, source_sha, *, allow_write=False):
    if (type(run_id) is not str or re.fullmatch(r'[1-9][0-9]{0,24}', run_id) is None
            or type(source_sha) is not str or re.fullmatch(r'[0-9a-f]{40}', source_sha) is None
            or type(allow_write) is not bool):
        raise ValueError('Explicit run and source binding required')
    job = 'NXS-LIVE-CHECKPOINT-' + run_id
    binding = dict(run_id=job, source_id='github-actions:' + run_id,
        source_sha256=hashlib.sha256(('checkpoint-write-probe:' + run_id).encode()).hexdigest(),
        destination_id=AUDIT_ID, policy_revision=POLICY, code_revision=source_sha, schema_version=1)
    checkpoint = encode(dict(binding=binding, receipts=(), pending=None), binding)
    event = dict(event_type='NXS_CHECKPOINT_V1', run_id=job, page_id=AUDIT_ID,
        sequence=0, previous=None, checkpoint=checkpoint)
    text = '\n```json\n' + canonical(event) + '\n```\n'
    reads = 0
    writes = 0
    def bounded(method, path, payload):
        nonlocal reads, writes
        if method == 'PATCH':
            if not allow_write or writes:
                raise ValueError('One write attempt only')
            writes += 1  # Count before request: failure never means no effect.
        elif method == 'GET':
            reads += 1
            if reads > 22:
                raise ValueError('Read request budget exhausted')
        else:
            raise ValueError('Method refused')
        return request(method, path, payload)
    api = NotionCheckpointAPI(AUDIT_ID, bounded, write_enabled=allow_write)
    transport = AuditCheckpointTransport(AUDIT_ID, binding, api.fetch_page, api.append_text)
    summary = dict(marker=job, destination=AUDIT_ID, source_revision=source_sha,
        checkpoint_sha256=hashlib.sha256(checkpoint.encode()).hexdigest(),
        execution_mode='FIRST_ATTEMPT_WRITE_ELIGIBLE' if allow_write else 'RERUN_OBSERVE_ONLY',
        checkpoint_state='UNKNOWN', write_outcome='NOT_ATTEMPTED',
        bridge_activation='INACTIVE', cp09='NOT_PROVEN', cleanup='RETAIN_MARKED_EVIDENCE')
    try:
        # Only the exact missing-enrollment disposition permits creating this test record.
        # Malformed JSON, unknown content, incomplete inventory and wrong bindings hold.
        try:
            before = transport._events()
        except ValueError as error:
            if str(error) != 'Explicit enrollment missing; no write permitted':
                raise
            before = []
        if before:
            if before != [event]:
                raise ValueError('Existing test checkpoint mismatch')
            summary['checkpoint_state'] = 'CHECKPOINT_ALREADY_PRESENT'
            return dict(summary, result='VERIFIED_ALREADY_PRESENT', reads=reads, writes_attempted=writes)
        summary['checkpoint_state'] = 'CHECKPOINT_ABSENT'
        if not allow_write:
            return dict(summary, result='BLOCKED_OBSERVE_ONLY_ABSENT', reads=reads, writes_attempted=writes)
        uncertain = False
        try:
            api.append_text(AUDIT_ID, text)
            summary['write_outcome'] = 'ACKNOWLEDGED'
        except Exception:
            uncertain = True
            if writes:
                summary['write_outcome'] = 'WRITE_OUTCOME_UNCERTAIN'
        # A fresh complete observation is mandatory even after success or lost ack.
        summary['checkpoint_state'] = 'UNKNOWN'
        try:
            observed = transport._events()
        except ValueError as error:
            if str(error) == 'Explicit enrollment missing; no write permitted':
                summary['checkpoint_state'] = 'CHECKPOINT_ABSENT'
            raise
        if observed != [event]:
            raise ValueError('Independent readback mismatch')
        summary['checkpoint_state'] = 'CHECKPOINT_ALREADY_PRESENT'
        return dict(summary, result='VERIFIED_AFTER_UNCERTAIN_ACK' if uncertain else 'VERIFIED',
            reads=reads, writes_attempted=writes, write_ack='UNCERTAIN' if uncertain else 'RECEIVED')
    except Exception:
        return dict(summary, result='BLOCKED_UNCERTAIN' if writes else 'BLOCKED_BEFORE_WRITE',
            reads=reads, writes_attempted=writes, next_action='OBSERVE_ONLY_NO_BLIND_RETRY')


def main():
    if (os.environ.get('GITHUB_REPOSITORY') != 'sovereignmystic92-dot/nexus-v3-sandbox-'
            or os.environ.get('GITHUB_REF') != 'refs/heads/main'
            or os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
            or os.environ.get('NOTION_CHECKPOINT_TEST_CONFIRMED') != 'true'):
        print('{"result":"SKIPPED"}')
        return 2
    try:
        attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '')
        if re.fullmatch(r'[1-9][0-9]*', attempt) is None:
            raise ValueError('Attempt identity missing')
        allow_write = attempt == '1'
        client = NotionRequest(AUDIT_ID, os.environ.pop('NOTION_SANDBOX_TOKEN', ''),
            '2022-06-28', write_enabled=allow_write)
        def paced(method, path, payload):
            time.sleep(0.4)
            return client(method, path, payload)
        result = probe(paced, os.environ.get('GITHUB_RUN_ID'), os.environ.get('GITHUB_SHA'),
            allow_write=allow_write)
    except Exception:
        print('{"result":"BLOCKED","reason":"CONFIGURATION_OR_REQUEST_UNAVAILABLE"}')
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result['result'].startswith('VERIFIED') else 2


if __name__ == '__main__':
    raise SystemExit(main())
