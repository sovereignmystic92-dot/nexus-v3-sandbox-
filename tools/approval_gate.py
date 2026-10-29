"""Fail-closed approval preflight; public GitHub reads only, never a write token.

Trust comes from base-branch code/config and provisioned GitHub reviewer identities.
Model identity and independence are reviewer attestations, not provider attestation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

REPOSITORY = 'sovereignmystic92-dot/nexus-v3-sandbox-'
API = 'https://api.github.com/repos/' + REPOSITORY
ROOT = Path(__file__).resolve().parents[1]
SAFE = {'offline_validation', 'read_only_probe', 'confirmed_synthetic_pilot'}
DELEGATED = {'routine_write', 'production_deployment'}
RESERVED = {'permission_expansion', 'credential_change', 'destructive_action'}


class Hold(ValueError):
    pass


def exact_sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise Hold('Exact revision required')
    return value


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise Hold('Duplicate JSON field')
        value[key] = item
    return value


def reject_constant(value):
    raise Hold('Nonstandard JSON constant')


def load_json(value):
    return json.loads(value, object_pairs_hook=unique_object, parse_constant=reject_constant)


def validate_policy(policy):
    if (type(policy) is not dict or
            set(policy) != {'policy_version', 'trusted_reviewers', 'destinations', 'workflows'} or
            type(policy['policy_version']) is not str or not policy['policy_version'].strip()):
        raise Hold('Invalid policy schema')
    trusted = policy['trusted_reviewers']
    if type(trusted) is not dict:
        raise Hold('Invalid trusted reviewers')
    for actor, identity in trusted.items():
        if (type(actor) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', actor) or
                type(identity) is not dict or set(identity) != {'provider'} or
                type(identity['provider']) is not str or not identity['provider'].strip()):
            raise Hold('Invalid reviewer identity')
    destinations = policy['destinations']
    if type(destinations) is not dict or any(k not in DELEGATED for k in destinations):
        raise Hold('Invalid destination policy')
    for values in destinations.values():
        if (type(values) is not list or any(type(v) is not str or not v.strip() for v in values) or
                len(values) != len(set(values))):
            raise Hold('Destination list required')
    workflows = policy['workflows']
    if (type(workflows) is not dict or
            any(type(k) is not str or not k or v not in SAFE for k, v in workflows.items())):
        raise Hold('Invalid workflow policy')
    return policy


def valid_evidence_url(url, revision):
    prefix = f'https://github.com/{REPOSITORY}/'
    if type(url) is not str or len(url) > 500:
        return False
    if re.fullmatch(re.escape(prefix) + r'actions/runs/[1-9][0-9]*', url):
        return True
    blob_prefix = prefix + 'blob/' + revision + '/'
    if not url.startswith(blob_prefix):
        return False
    parts = url[len(blob_prefix):].split('/')
    return all(part not in {'', '.', '..'} and
               re.fullmatch(r'[A-Za-z0-9_.-]+', part) for part in parts)



class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Hold('Unexpected API redirect')


def public_get(path):
    # Callers supply fixed API paths and validated numeric IDs or exact SHAs.
    request = urllib.request.Request(API + path, headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'nexus-approval-gate',
        'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise Hold('API response exceeds bound')
    return load_json(data)


def review_list(pr_number, get=public_get):
    reviews = []
    for page in range(1, 11):
        batch = get(f'/pulls/{pr_number}/reviews?per_page=100&page={page}')
        if not isinstance(batch, list):
            raise Hold('Invalid review response')
        reviews.extend(batch)
        if len(batch) < 100:
            return reviews
    raise Hold('Review pagination incomplete')


def preflight(policy, workflow, revision):
    validate_policy(policy)
    exact_sha(revision)
    operation = policy['workflows'].get(workflow)
    if operation not in SAFE:
        raise Hold('Workflow lacks a reviewed nonconsequential classification')
    return {'verdict': 'EXEMPT_FROM_TWO_AI_APPROVAL', 'operation': operation,
            'workflow': workflow, 'revision': revision,
            'scope': 'Existing manual confirmations and provider controls still apply'}


def authorize(policy, pr, reviews, revision, operation, destination, request_sha256=None):
    validate_policy(policy)
    exact_sha(revision)
    if request_sha256 is None:
        request_sha256 = hashlib.sha256(json.dumps(
            [revision, operation, destination], separators=(',', ':')).encode()).hexdigest()
    if not isinstance(request_sha256, str) or not re.fullmatch('[0-9a-f]{64}', request_sha256):
        raise Hold('Exact request hash required')
    if operation in RESERVED:
        raise Hold('Explicit owner approval required; AI delegation is insufficient')
    if operation not in DELEGATED:
        raise Hold('Unknown consequential operation')
    if destination not in policy['destinations'].get(operation, []):
        raise Hold('Destination not provisioned for delegated approval')
    if pr.get('head', {}).get('sha') != revision or pr.get('state') != 'open':
        raise Hold('Review revision is not the current open PR head')
    if pr.get('base', {}).get('ref') != 'main':
        raise Hold('Only main-targeted PRs are supported')
    if pr.get('base', {}).get('repo', {}).get('full_name') != REPOSITORY:
        raise Hold('Wrong repository')
    if pr.get('head', {}).get('repo', {}).get('full_name') != REPOSITORY:
        raise Hold('Fork approvals are outside configured scope')
    trusted = policy['trusted_reviewers']
    author = pr.get('user', {}).get('login')
    latest = {}
    # COMMENTED reviews do not revoke native GitHub approval. Changes requested,
    # dismissal, and newer approvals (including other SHAs) replace old decisions.
    for review in sorted(reviews, key=lambda r: int(r['id'])):
        actor = review.get('user', {}).get('login')
        if review.get('state') in {'APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'}:
            latest[actor] = review
    accepted = []
    for actor, review in latest.items():
        if actor not in trusted or actor == author:
            continue
        if review['state'] != 'APPROVED' or review.get('commit_id') != revision:
            raise Hold('Trusted reviewer has no current-revision approval')
        try:
            receipt = load_json(review.get('body', ''))
        except (ValueError, TypeError):
            raise Hold('Trusted approval lacks a valid structured receipt') from None
        required = {'policy_version', 'revision', 'operation', 'destination',
                    'session_id', 'model', 'provider', 'verdict', 'evidence',
                    'findings', 'prior_conclusions_seen', 'limitations', 'request_sha256'}
        if not isinstance(receipt, dict) or set(receipt) != required:
            raise Hold('Approval receipt fields differ from contract')
        if (receipt['policy_version'] != policy['policy_version'] or
                receipt['revision'] != revision or receipt['operation'] != operation or
                receipt['destination'] != destination or receipt['verdict'] != 'PASS' or
                receipt['request_sha256'] != request_sha256 or
                receipt['provider'] != trusted[actor]['provider'] or
                receipt['prior_conclusions_seen'] is not False or receipt['findings'] != []):
            raise Hold('Approval receipt does not satisfy requested operation')
        if any(not isinstance(receipt[k], str) or not receipt[k].strip() or receipt[k] != receipt[k].strip()
               or len(receipt[k]) > 200 for k in ('session_id', 'model', 'provider')):
            raise Hold('Reviewer identity missing or oversized')
        evidence = receipt['evidence']
        if (not isinstance(evidence, list) or not 1 <= len(evidence) <= 20 or
                any(not valid_evidence_url(url, revision) for url in evidence)):
            raise Hold('Evidence must identify repository runs or exact-revision files')
        if (not isinstance(receipt['limitations'], list) or
                any(not isinstance(item, str) or len(item) > 1000
                    for item in receipt['limitations'])):
            raise Hold('Invalid limitations')
        accepted.append((actor, receipt['session_id'], review['id']))
    if len(accepted) < 2 or len({r[1] for r in accepted}) != len(accepted):
        raise Hold('Two distinct trusted reviewers and independent sessions required')
    return {'verdict': 'REVIEW_RECEIPTS_ACCEPTED', 'revision': revision,
            'operation': operation, 'destination': destination,
            'request_sha256': request_sha256,
            'review_ids': [r[2] for r in accepted],
            'scope': 'Authenticated reviewer attestations; technical readiness remains separate'}


def recheck_pr_context(before, after, revision):
    """Reject material PR drift across observation; no approval or dispatch here."""
    exact_sha(revision)
    def context(pr):
        try:
            head, base, author = pr['head'], pr['base'], pr['user']['login']
            exact_sha(head['sha'])
            exact_sha(base['sha'])
            if (pr['state'] != 'open' or head['sha'] != revision or
                    base['ref'] != 'main' or
                    head['repo']['full_name'] != REPOSITORY or
                    base['repo']['full_name'] != REPOSITORY or
                    type(author) is not str or not author.strip()):
                raise Hold('Invalid PR context')
            return (head['sha'], base['sha'], base['ref'],
                    head['repo']['full_name'], base['repo']['full_name'], author)
        except (KeyError, TypeError, AttributeError):
            raise Hold('PR context unavailable') from None
    if context(before) != context(after):
        raise Hold('PR context changed during approval check')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, default=ROOT / 'tools/approval_policy.json')
    parser.add_argument('--revision', required=True)
    parser.add_argument('--workflow')
    parser.add_argument('--pr', type=int)
    parser.add_argument('--operation', default='routine_write')
    parser.add_argument('--destination', default='github:main')
    parser.add_argument('--request-sha256')
    args = parser.parse_args()
    try:
        policy = validate_policy(load_json(args.policy.read_text()))
        exact_sha(args.revision)
        if args.workflow:
            if args.pr is not None:
                raise Hold('Preflight cannot substitute for consequential approval')
            result = preflight(policy, args.workflow, args.revision)
        else:
            if args.pr is None or args.pr <= 0:
                raise Hold('Positive PR number required')
            # No provisioned reviewer identities: stop before network access.
            if len(policy['trusted_reviewers']) < 2:
                raise Hold('Trusted AI reviewer identities are not provisioned')
            before = public_get(f'/pulls/{args.pr}')
            result = authorize(policy, before, review_list(args.pr), args.revision,
                               args.operation, args.destination, args.request_sha256)
            after = public_get(f'/pulls/{args.pr}')
            recheck_pr_context(before, after, args.revision)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        # No response bodies, credentials or untrusted review text in public logs.
        print(json.dumps({'verdict': 'HOLD',
                          'reason': 'Approval evidence unavailable, invalid, or not provisioned'}))
        return 2


if __name__ == '__main__':
    sys.exit(main())

