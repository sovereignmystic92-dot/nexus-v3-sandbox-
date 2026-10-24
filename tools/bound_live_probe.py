"""Opt-in bounded live probe through an operator-host JSON-line callback.

No credentials or network driver. Initial observations and plan are private.
Run write once, then reconcile in a new process with the original journal/plan.
"""
import argparse
from dataclasses import asdict,replace
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from nexus_sandbox.bound_cortex_tools import BoundCortexToolTransport,FixtureBinding
from nexus_sandbox.cortex_adapter import CortexAdapter,Module,Write,MARKER
from nexus_sandbox.cortex_tools import ToolFailure


def module(value):
    return Module(value['id'],value['name'],value['version'],value['content'],tuple(value['dependencies']))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('write','reconcile'),required=True)
    p.add_argument('--initial',type=Path)
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--journal',type=Path,required=True)
    p.add_argument('--resume-preflight',action='store_true',help='Reuse original plan only after interrupted read-only setup; journal must be absent')
    args=p.parse_args()
    if sys.stdin.isatty():
        import termios
        settings=termios.tcgetattr(sys.stdin);settings[3] &= ~termios.ECHO
        termios.tcsetattr(sys.stdin,termios.TCSANOW,settings)
    if args.mode=='write' and not args.resume_preflight:
        if args.plan.exists() or args.journal.exists():raise RuntimeError('Retain existing state and reconcile; never reset')
        initial=json.loads(args.initial.read_text());names=initial['names']
        rows={name:json.loads(result['content'][0]['text']) for name,result in initial['reads'].items()}
        root,source,target=(rows[names[k]] for k in ('root','source','target'))
        if any(row['version']!=1 for row in rows.values()):raise RuntimeError('Expected new synthetic v1 fixtures')
        key='synthetic:request:cp05-bound-live-update'
        request=Write(key,target['name'],MARKER+'\n'+key+'\nBounded live target version two.',
                      tuple(target['dependencies']),module(source),module(target))
        data={'names':names,'root_version':root['version'],
              'root_hash':hashlib.sha256(root['content'].encode()).hexdigest(),
              'root_dependencies':root['dependencies'],
              'bindings':[{'name':r['name'],'module_id':r['id'],'owner':r['owner'],'parent':r['parent']} for r in rows.values()],
              'request':asdict(request),'before_metadata':rows}
        with args.plan.open('x') as f:json.dump(data,f)
    else:
        if args.resume_preflight:
            if args.mode!='write' or not args.plan.exists() or args.journal.exists():
                raise RuntimeError('Read-only preflight resume requires intact plan and absent journal')
        elif not args.plan.exists() or not args.journal.exists():raise RuntimeError('Original plan/journal required')
        data=json.loads(args.plan.read_text());names=data['names'];r=data['request']
        request=Write(r['key'],r['name'],r['content'],tuple(r['dependencies']),module(r['source']),module(r['before']))
    bindings=tuple(FixtureBinding(**v) for v in data['bindings'])
    calls=[];phase='negative';writes=0
    def invoke(tool,arguments):
        nonlocal writes
        if tool=='context_get':
            if arguments['name'] not in names.values():raise RuntimeError('Out-of-scope read')
        elif (tool=='context_update' and args.mode=='write' and phase=='positive' and writes==0
              and arguments=={'name':request.name,'content':request.content,'dependencies':list(request.dependencies)}):
            writes+=1
        else:raise RuntimeError('Host operation scope violation')
        print(json.dumps({'rpc':tool,'arguments':arguments}),flush=True)
        line=sys.stdin.readline()
        if not line:raise RuntimeError('Host disconnected; retain journal/plan')
        result=json.loads(line);calls.append({'tool':tool,'name':arguments['name'],'isError':bool(result.get('isError'))})
        return result
    def transport(selected=bindings):
        return BoundCortexToolTransport(invoke,selected,names['root'],data['root_version'],data['root_hash'],tuple(data['root_dependencies']))
    negative=[]
    if args.mode=='write':
        if args.resume_preflight:
            if transport().get(request.source.name)!=request.source or transport().get(request.name)!=request.before:
                raise RuntimeError('Preflight baseline changed; do not resume writer')
        for label,field in (('wrong_root_id','module_id'),('wrong_root_owner','owner')):
            changed=tuple(replace(b,**{field:'synthetic:wrong-binding'}) if b.name==names['root'] else b for b in bindings)
            try:transport(changed).update(request.name,request.content,request.dependencies)
            except ToolFailure:negative.append(label)
            else:raise RuntimeError('Negative binding accepted')
        try:transport().update('Nexus Sandbox Unenrolled Target',request.content,request.dependencies)
        except ToolFailure:negative.append('unenrolled_destination')
        else:raise RuntimeError('Unenrolled target accepted')
        if writes:raise RuntimeError('Negative phase mutated provider')
    phase='positive'
    outcomes=[]
    for _ in range(2):
        result=CortexAdapter(args.journal,frozenset(names.values()),transport()).ensure(request)
        outcomes.append(asdict(result))
        if result.protocol_verdict!='VERIFIED':raise RuntimeError('Hold; retain state for investigation')
    expected='SUCCEEDED' if args.mode=='write' else 'NOT_ATTEMPTED'
    if outcomes[0]['operation_outcome']!=expected or outcomes[1]['operation_outcome']!='NOT_ATTEMPTED':
        raise RuntimeError('Unexpected operation outcome')
    if writes!=(1 if args.mode=='write' else 0):raise RuntimeError('Unexpected provider mutation count')
    print(json.dumps({'probe_result':'PASSED','mode':args.mode,'outcomes':outcomes,'negative_cases':negative,
                      'provider_updates':writes,'calls':calls,
                      'limitations':['Pinned module ownership is not authenticated caller identity','Host-mediated, single worker; no provider CAS or complete host-tool coverage']}),flush=True)


if __name__=='__main__':main()
