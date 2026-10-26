"""Read-only CI evidence bridge; injected retrieval, no credentials or repair."""
import hashlib
import re

from failure_handoff import collect, InvalidEvidence


def require(value):
    if not value:
        raise InvalidEvidence('Unbound or incomplete CI evidence')


def extract_cases(log):
    """Accept one bounded, complete verbose unittest stream, otherwise no cases.

    A caller must bind the original stream to the exact run attempt/job.
    Raw text is never returned, evaluated, or used as a command.
    """
    require(type(log) is str and len(log.encode('utf-8')) <= 2 * 1024 * 1024)
    rows = re.findall(r'^([A-Za-z0-9_]+) \(([A-Za-z0-9_.]+)\) \.\.\. (ok|FAIL|ERROR|skipped .*)$', log, re.M)
    summaries = re.findall(r'^Ran (\d+) tests? in [0-9.]+s$', log, re.M)
    endings = re.findall(r'^(OK|FAILED \([^\n]+\))$', log, re.M)
    if len(summaries) != 1 or len(endings) != 1 or int(summaries[0]) != len(rows) or not rows:
        return []
    failures = [(name, owner, result) for name, owner, result in rows if result in ('FAIL', 'ERROR')]
    if bool(failures) != endings[0].startswith('FAILED'):
        return []
    cases = []
    for name, owner, result in rows:
        # Python unittest versions differ: newer output includes the method in
        # the parenthesized full ID; older output includes only module/class.
        identity = owner if owner.endswith('.' + name) else owner + '.' + name
        status = {'ok': 'PASSED', 'FAIL': 'FAILED', 'ERROR': 'ERROR'}.get(result, 'SKIPPED')
        signature = None
        if status in ('FAILED', 'ERROR'):
            # Require the diagnostic section; never manufacture a traceback.
            header = ('FAIL' if status == 'FAILED' else 'ERROR') + ': ' + name + ' (' + owner + ')'
            parts = log.split(header + '\n')
            if len(parts) != 2:
                return []
            diagnostic = re.sub(r'^-{10,}\n', '', parts[1], count=1)
            detail = re.split(r'^={10,}$|^-{10,}$', diagnostic, flags=re.M)[0].strip()
            if not detail:
                return []
            signature = hashlib.sha256(detail.encode()).hexdigest()
        cases.append({'test_id': identity, 'status': status, 'failure_signature': signature})
    if len({c['test_id'] for c in cases}) != len(cases):
        return []
    return cases


def retrieve(repository, current_sha, run_id, attempt, fetch_json, read_job_log=None,
             case_parser=extract_cases):
    """Fetch exact attempt metadata/jobs; log reader is optional and read-only.

    fetch_json accepts only relative GitHub repository paths. The host owns
    authenticated transport and bounded JSON decoding. No latest-attempt fallback.
    """
    require(type(repository) is str and re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository))
    require(type(current_sha) is str and re.fullmatch(r'[0-9a-f]{40}', current_sha))
    require(type(run_id) is int and run_id > 0 and type(attempt) is int and attempt > 0)
    prefix = '/repos/' + repository + '/actions/runs/' + str(run_id) + '/attempts/' + str(attempt)
    run = fetch_json(prefix)
    require(type(run) is dict and run.get('id') == run_id and run.get('run_attempt') == attempt)
    require(run.get('repository', {}).get('full_name') == repository)
    require(type(run.get('head_sha')) is str and re.fullmatch(r'[0-9a-f]{40}', run['head_sha']))
    jobs = []; total = None
    for page in range(1, 11):
        response = fetch_json(prefix + '/jobs?per_page=100&page=' + str(page))
        require(type(response) is dict and type(response.get('total_count')) is int)
        require(type(response.get('jobs')) is list and len(response['jobs']) <= 100)
        if total is None: total = response['total_count']
        require(response['total_count'] == total and 0 <= total <= 1000)
        jobs.extend(response['jobs'])
        if len(jobs) >= total: break
        require(len(response['jobs']) == 100)
    require(len(jobs) == total)
    seen = set(); cases = []; log_reads = 0; complete = bool(jobs)
    for job in jobs:
        require(type(job) is dict and type(job.get('id')) is int and job['id'] > 0)
        require(job['id'] not in seen); seen.add(job['id'])
        require(job.get('run_id') == run_id and job.get('run_attempt') == attempt and job.get('head_sha') == run['head_sha'])
        parsed = []
        if read_job_log is not None and job.get('status') == 'completed':
            log = read_job_log(job['id'], run_id, attempt)
            log_reads += 1
            if log is not None: parsed = case_parser(log)
        complete = complete and bool(parsed)
        cases.extend(parsed)
    # Partial suites cannot support a clean or actionable failure verdict.
    if not complete: cases = []
    report = dict(repository=repository, run_id=run_id, attempt=attempt,
                  source_sha=run['head_sha'], status=run.get('status'),
                  conclusion=run.get('conclusion'), cases=cases)
    result = collect(dict(repository=repository, current_sha=current_sha, reports=[report]))
    return {'handoff': result, 'provenance': {'repository': repository, 'run_id': run_id,
            'attempt': attempt, 'source_sha': run['head_sha'], 'job_ids': sorted(seen),
            'job_inventory_complete': True, 'case_evidence_complete': complete,
            'log_reads': log_reads, 'transport': 'host-injected read-only retrieval'}}
