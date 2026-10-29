"""Bounded tool-mediated audit receipt runner. No HTTP client or credentials.

The surrounding trusted host services JSON-line requests with actual Notion MCP
calls and supplies independently observed review records. Not a background hook.
"""
import json
from pathlib import Path
import sys

from approval_gate import Hold
from declared_notion_write import execute
from write_journal_custody import JournalCustody, restore

AUDIT = 'notion:4018c067-daa4-8122-b82e-c2ae8067d021'


def run(config, call):
    if (config['enrolled_destination'] != AUDIT
            or config['context']['destination'] != AUDIT):
        raise Hold('Only canonical Foundation Audit is enrolled in this runner')
    target = config['payload']
    receipt = target.get('receipt') if type(target) is dict else None
    if (set(target) != {'receipt'} or type(receipt) is not dict
            or set(receipt) != {'schema', 'request_id', 'source_id', 'operation', 'result'}
            or receipt['schema'] != 'NXS_TOOL_HANDOFF_RECEIPT_V1'
            or receipt['request_id'] != config['request_id']
            or receipt['operation'] != 'audit_receipt'
            or receipt['result'] != 'LIVE_RECEIPT_SUBMITTED'
            or type(receipt['source_id']) is not str or not receipt['source_id']):
        raise Hold('One bound additive audit receipt required')
    path = config['journal']
    custody = JournalCustody(
        lambda value, digest: call('journal_publish', dict(destination=AUDIT,
            envelope=value, expected_sha256=digest)),
        lambda identity: call('journal_fetch', dict(destination=AUDIT, record_id=identity)))
    mode = config['journal_mode']
    if mode == 'restore':
        saved = config['saved_custody']
        envelope = call('journal_fetch', dict(destination=AUDIT, record_id=saved['record_id']))
        restore(path, envelope, expected_digest=saved['sha256'],
                request_id=config['request_id'], context=config['context'])
    elif mode == 'new':
        if (Path(path).exists() or config.get('saved_custody') is not None
                or call('confirm_new_enrollment', dict(destination=AUDIT,
                    request_id=config['request_id'], context=config['context'])) is not True):
            raise Hold('Explicit fresh operation enrollment required; no lost-journal fallback')
    else:
        raise Hold('Choose explicit new or externally restored journal')

    def read(destination):
        observed = call('notion_read_receipt', dict(destination=destination,
                                                   request_id=config['request_id']))
        if (type(observed) is not dict or set(observed) != {'complete', 'destination', 'value'}
                or observed['complete'] is not True or observed['destination'] != AUDIT):
            raise Hold('Complete bound receipt observation required')
        return observed['value']

    return execute(path, request_id=config['request_id'], context=config['context'],
        author_session=config['author_session'], owner_decision=config['owner_decision'],
        enrolled_destination=AUDIT, before_hash=config['before_hash'], payload=target,
        observe=lambda: call('observe_reviews', dict(context=config['context'])), read=read,
        write=lambda destination, value: call('notion_append_receipt',
            dict(destination=destination, receipt=value['receipt'])), custody=custody)


def main():
    # The host must preserve config/review anchors outside this temporary process.
    config = json.loads(sys.stdin.readline())
    sequence = 0

    def call(method, params):
        nonlocal sequence
        sequence += 1
        print(json.dumps(dict(id=sequence, method=method, params=params)), flush=True)
        response = json.loads(sys.stdin.readline())
        if (type(response) is not dict or set(response) != {'id', 'result'}
                or response['id'] != sequence):
            raise Hold('Missing or misbound host response; reconcile without replay')
        return response['result']

    try:
        result = run(config, call)
        print(json.dumps(dict(result=result)), flush=True)
    except Exception:
        print(json.dumps(dict(error='HOLD; preserve custody and reconcile without replay')), flush=True)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
