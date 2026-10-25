"""Verify secret-free CI source against the current remote merge parents."""
import json
import os
import re
import subprocess

REPOSITORY = 'https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-.git'


def git(*args):
    return subprocess.check_output(['git', '-c', 'credential.helper=', *args],
                                   text=True, timeout=30).strip()


def verify(env, run_git=git):
    event, ref, sha = (env.get(k, '') for k in ('SOURCE_EVENT', 'SOURCE_REF', 'SOURCE_SHA'))
    base, head, base_ref = (env.get(k, '') for k in ('PR_BASE_SHA', 'PR_HEAD_SHA', 'PR_BASE_REF'))
    if not re.fullmatch(r'[0-9a-f]{40}', sha) or run_git('rev-parse', 'HEAD') != sha:
        raise ValueError('Exact checked-out revision required')
    raw = run_git('cat-file', '-p', 'HEAD')
    parents = [line.split(' ', 1)[1] for line in raw.split('\n\n', 1)[0].splitlines()
               if line.startswith('parent ')]
    observed_base = ''
    if event == 'pull_request':
        if not re.fullmatch(r'refs/pull/[0-9]+/merge', ref):
            raise ValueError('Expected a pull-request merge ref')
        if not base_ref or not all(re.fullmatch(r'[0-9a-f]{40}', v) for v in (base, head)):
            raise ValueError('Unexpected PR base/ref metadata')
        # No branch allowlist: future stacked targets receive the same checks.
        # Validate as a Git ref before using the value as a remote ref argument.
        run_git('check-ref-format', 'refs/heads/' + base_ref)
        fields = run_git('ls-remote', '--exit-code', REPOSITORY,
                         'refs/heads/' + base_ref).split()
        if (len(fields) != 2 or fields[1] != 'refs/heads/' + base_ref
                or not re.fullmatch(r'[0-9a-f]{40}', fields[0])):
            raise ValueError('Current PR base branch could not be established')
        observed_base = fields[0]
        if parents != [observed_base, head]:
            raise ValueError('Merge candidate differs from current base branch or event head')
    elif event != 'push' or not ref.startswith('refs/heads/'):
        raise ValueError('Unexpected source event/ref')
    return {'event': event, 'ref': ref, 'sha': sha, 'base_sha': observed_base or base,
            'event_base_sha': base, 'base_ref': base_ref, 'observed_base_sha': observed_base,
            'event_base_matches_candidate': base == observed_base if event == 'pull_request' else None,
            'head_sha': head, 'parents': parents, 'merge_candidate_checked': event == 'pull_request'}


if __name__ == '__main__':
    result = verify(os.environ)
    print(json.dumps({'ci_source': result}, sort_keys=True))
    # Subsequent ledger preflight must compare against the verified current base,
    # including when the event payload carries an older base SHA.
    if result['event'] == 'pull_request' and os.environ.get('GITHUB_ENV'):
        with open(os.environ['GITHUB_ENV'], 'a') as target:
            target.write('PR_BASE_SHA=' + result['observed_base_sha'] + '\n')
