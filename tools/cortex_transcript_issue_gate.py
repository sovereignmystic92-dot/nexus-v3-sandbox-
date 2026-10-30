"""GitHub issue-event -> Nexus synthetic transcription observation (read-only).

This is a handoff smoke test. GitHub issue authorship is NOT Cortex event
authentication. No API credentials, provider writes or automatic research.
"""
import json
import re
import sys

PREFIX = "NEXUS_TRANSCRIPT_EVENT_V1\n"
FIELDS = {'schema', 'cortex_issue_id', 'event_id', 'source_ref', 'source_sha256', 'event_kind'}
DIGEST = re.compile(r'^[0-9a-f]{64}$')
IDENT = re.compile(r'^[a-zA-Z0-9_:-]{1,128}$')


def inspect_issue_event(payload):
    hold = dict(status='HELD', next_action='REVIEW_EVENT_BINDING',
                provider_writes=0, automatic_execution=False,
                cp09='NOT_PROVEN')
    if type(payload) is not dict or payload.get('action') != 'opened':
        return hold
    repo = payload.get('repository')
    sender = payload.get('sender')
    issue = payload.get('issue')
    if not all(type(v) is dict for v in (repo, sender, issue)):
        return hold
    if repo.get('full_name') != 'sovereignmystic92-dot/nexus-v3-sandbox-':
        return hold
    if sender.get('login') != 'sovereignmystic92-dot':
        return hold
    if (type(issue.get('user')) is not dict or
            issue['user'].get('login') != 'sovereignmystic92-dot' or
            issue.get('title') != '[Nexus synthetic transcript event]'):
        return hold
    body = issue.get('body')
    if type(body) is not str or not body.startswith(PREFIX) or len(body) > 4096:
        return hold
    try:
        def unique(pairs):
            out = {}
            for k, v in pairs:
                if k in out:
                    raise ValueError('duplicate')
                out[k] = v
            return out
        data = json.loads(body[len(PREFIX):], object_pairs_hook=unique)
    except (ValueError, TypeError):
        return hold
    if type(data) is not dict or set(data) != FIELDS:
        return hold
    if any(type(v) is not str for v in data.values()):
        return hold
    if (data['schema'] != 'NEXUS_TRANSCRIPT_EVENT_V1' or
            data['event_kind'] != 'SOURCE_READY' or
            IDENT.fullmatch(data['cortex_issue_id']) is None or
            IDENT.fullmatch(data['event_id']) is None or
            not data['source_ref'].startswith('synthetic:transcript:') or
            len(data['source_ref']) > 128 or
            DIGEST.fullmatch(data['source_sha256']) is None):
        return hold
    return dict(status='OBSERVED', next_action='INSPECT_TRANSCRIPT_PLAN_ONLY',
                event_id=data['event_id'], cortex_issue_id=data['cortex_issue_id'],
                source_ref=data['source_ref'], source_sha256=data['source_sha256'],
                github_issue_number=issue.get('number'),
                provider_writes=0, automatic_execution=False,
                cp09='NOT_PROVEN')


def main():
    if len(sys.argv) != 2:
        return 2
    try:
        from pathlib import Path
        file = Path(sys.argv[1])
        if file.stat().st_size > 1048576:
            raise ValueError('oversize')
        payload = json.loads(file.read_text(encoding='utf-8'))
        outcome = inspect_issue_event(payload)
    except (OSError, ValueError, UnicodeError):
        outcome = dict(status='HELD', next_action='REVIEW_EVENT_BINDING',
                       provider_writes=0, automatic_execution=False, cp09='NOT_PROVEN')
    print(json.dumps(outcome, sort_keys=True))
    return 0 if outcome['status'] == 'OBSERVED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
