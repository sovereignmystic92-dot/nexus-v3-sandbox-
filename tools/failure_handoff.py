"""Offline CI-result normalization. No provider calls, patches or gate changes."""
import argparse
import hashlib
import json
from pathlib import Path
import re


class InvalidEvidence(ValueError):
    pass


def require(condition):
    if not condition:
        raise InvalidEvidence('Incomplete or inconsistent CI evidence')


def collect(packet):
    require(type(packet) is dict and set(packet)=={'repository','current_sha','reports'})
    repo, current, reports=packet['repository'],packet['current_sha'],packet['reports']
    require(isinstance(repo,str) and re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo))
    require(isinstance(current,str) and re.fullmatch(r'[0-9a-f]{40}',current))
    require(type(reports) is list and len(reports)<=100)
    groups={}
    for report in reports:
        require(type(report) is dict and set(report)=={'repository','run_id','attempt','source_sha','status','conclusion','cases'})
        require(report['repository']==repo and type(report['run_id']) is int and report['run_id']>0)
        require(type(report['attempt']) is int and report['attempt']>0)
        require(isinstance(report['source_sha'],str) and re.fullmatch(r'[0-9a-f]{40}',report['source_sha']))
        require(report['status'] in ('queued','pending','in_progress','completed'))
        require(report['conclusion'] in (None,'success','failure','cancelled','timed_out','action_required','neutral','skipped','startup_failure','stale'))
        require((report['status']=='completed')==(report['conclusion'] is not None))
        require(type(report['cases']) is list and len(report['cases'])<=10000)
        seen=set()
        for case in report['cases']:
            require(type(case) is dict and set(case)=={'test_id','status','failure_signature'})
            test_id=case['test_id']
            require(isinstance(test_id,str) and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,300}',test_id))
            require(test_id not in seen);seen.add(test_id)
            require(case['status'] in ('PASSED','FAILED','ERROR','SKIPPED'))
            signature=case['failure_signature']
            require(signature is None or isinstance(signature,str) and re.fullmatch(r'[0-9a-f]{64}',signature))
            require((case['status'] in ('FAILED','ERROR'))==(signature is not None))
        key=(report['run_id'],report['attempt'])
        if key in groups:require(groups[key]==report)
        groups[key]=report
    by_run={}
    for (run_id,attempt),report in groups.items():
        by_run.setdefault(run_id,[]).append(report)
    findings={};runs=[]
    for run_id,history in sorted(by_run.items()):
        history.sort(key=lambda r:r['attempt']);latest=history[-1]
        require(len({r['source_sha'] for r in history})==1)
        failures=[c for c in latest['cases'] if c['status'] in ('FAILED','ERROR')]
        if latest['source_sha']!=current:disposition='STALE_REVISION'
        elif latest['status']!='completed':disposition='PENDING'
        elif latest['conclusion']=='cancelled':disposition='CANCELLED'
        elif latest['conclusion'] in ('timed_out','startup_failure','action_required'):disposition='EXECUTION_BLOCKED'
        elif latest['conclusion']=='success' and failures:disposition='INCONSISTENT'
        elif latest['conclusion']=='success' and latest['cases'] and all(c['status']=='PASSED' for c in latest['cases']):disposition='HEALTHY'
        elif latest['conclusion']=='failure' and failures:disposition='TEST_FAILURE_OBSERVED'
        else:disposition='INCOMPLETE_EVIDENCE'
        runs.append({'run_id':run_id,'latest_attempt':latest['attempt'],'disposition':disposition,
                     'attempts_observed':[r['attempt'] for r in history],
                     'prior_failed_case_count':sum(c['status'] in ('FAILED','ERROR') for r in history[:-1] for c in r['cases'])})
        if disposition!='TEST_FAILURE_OBSERVED':continue
        for case in failures:
            identity=[repo,current,case['test_id'],case['status'],case['failure_signature']]
            key=hashlib.sha256(json.dumps(identity,separators=(',',':')).encode()).hexdigest()
            item=findings.setdefault(key,{'finding_id':key,'source_sha':current,'test_id':case['test_id'],
                'status':case['status'],'failure_signature':case['failure_signature'],'observations':[],
                'next_action':'Inspect and reproduce before drafting; no patch or gate acceptance authorized by this result',
                'repair_applied':False})
            item['observations'].append({'run_id':run_id,'attempt':latest['attempt']})
    return {'schema_version':1,'repository':repo,'current_sha':current,
            'assessment':'NO_EVIDENCE' if not runs else 'RESULTS_CLASSIFIED',
            'runs':runs,'findings':[findings[k] for k in sorted(findings)],
            'automation_scope':'Offline handoff only; no retrieval, scheduling, agent execution, writes or auto-merge'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('packet')
    args=parser.parse_args()
    try:
        raw=Path(args.packet).read_bytes()
        require(len(raw)<=2*1024*1024)
        def unique(pairs):
            result={}
            for key,value in pairs:
                require(key not in result);result[key]=value
            return result
        result=collect(json.loads(raw,object_pairs_hook=unique))
    except (OSError,ValueError,TypeError,RecursionError):
        print(json.dumps({'assessment':'INVALID_EVIDENCE','repair_applied':False}))
        return 2
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
