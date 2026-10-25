"""Bounded SIGTERM probe of the real runner and Docker, on a surviving host."""
import json
import os
from pathlib import Path
import select
import shutil
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DRIVER = r'''
import json,subprocess,sys,time
sys.path.insert(0,sys.argv[1]+'/tools')
import run_isolated as r
original_command=r.command
original_run=subprocess.run
owned={}
def command(args,**kwargs):
    if args[:2]==['docker','create']:
        args=list(args)
        owned['name']=args[args.index('--name')+1]
        mount=args[args.index('--mount')+1]
        owned['stage']=mount.split('src=',1)[1].split(',dst=',1)[0]
        args[-3:]=['python3','-c','import time; time.sleep(120)']
    return original_command(args,**kwargs)
r.command=command
def run(args,**kwargs):
    if args[:3]!=['docker','start','--attach']:
        return original_run(args,**kwargs)
    client=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            state=json.loads(original_command(['docker','inspect',owned['name']]))[0]['State']
            if state['Running']:
                print(json.dumps({'ready':owned}),flush=True)
                break
            time.sleep(.05)
        else:raise RuntimeError('Probe container did not start')
        out,err=client.communicate(timeout=25)
        return subprocess.CompletedProcess(args,client.returncode,out,err)
    finally:
        if client.poll() is None:
            client.terminate()
            try:client.wait(timeout=3)
            except subprocess.TimeoutExpired:client.kill();client.wait(timeout=3)
r.subprocess.run=run
sys.exit(r.main())
'''


def main():
    if not shutil.which('docker'):
        raise RuntimeError('Docker required; real-container stop probe not executed')
    child=subprocess.Popen([sys.executable,'-u','-c',DRIVER,str(ROOT)],
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    owned=None
    try:
        if not select.select([child.stdout],[],[],180)[0]:
            raise RuntimeError('Runner readiness timeout')
        first=child.stdout.readline()
        owned=json.loads(first).get('ready')
        if not owned:raise RuntimeError('Runner stopped before real container readiness')
        name=owned['name']
        if not name.startswith('nexus-acceptance-'):
            raise RuntimeError('Unexpected container identity')
        child.send_signal(signal.SIGTERM)
        out,err=child.communicate(timeout=90)
        report=json.loads(out)
        remaining=subprocess.run(['docker','ps','--all','--quiet','--filter','name=^/'+name+'$'],
                                 check=True,capture_output=True,text=True,timeout=10).stdout.strip()
        stage_parent=Path(owned['stage']).parent
        passed=(child.returncode==2 and report.get('isolated_run_status')=='BLOCKED'
                and 'SIGTERM' in report.get('blocker','')
                and report.get('container_removed') is True
                and report.get('source_staging_removed') is True
                and not remaining and not stage_parent.exists())
        print(json.dumps({'case_id':'REAL-DOCKER-RUNNER-SIGTERM',
            'status':'PASSED' if passed else 'FAILED',
            'container_absent':not remaining,'staging_absent':not stage_parent.exists(),
            'runner_report':report,'source_sha':os.environ.get('SOURCE_SHA'),
            'limits':['Catchable runner stop on surviving host; not SIGKILL or host/power loss',
                      'Synthetic waiting workload replaces the suite inside the normal real runner container',
                      'No retention deletion evidence or checkpoint closure']} ,sort_keys=True))
        return 0 if passed else 2
    finally:
        if child.poll() is None:
            child.kill();child.wait(timeout=5)
        if owned and owned['name'].startswith('nexus-acceptance-'):
            subprocess.run(['docker','rm','--force',owned['name']],capture_output=True,timeout=15)


if __name__=='__main__':
    result=main()
    if result==0:
        from real_container_kill_probe import run
        result=run()
    raise SystemExit(result)
