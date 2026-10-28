"""Owned-runner SIGKILL and surviving-supervisor cleanup; not host loss."""
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
from cleanup_handoff import Journal


def run():
    from real_container_stop_probe import DRIVER, ROOT
    root=Path(tempfile.mkdtemp(prefix='nexus-supervisor-')).resolve()
    custody=Path(tempfile.mkdtemp(prefix='nexus-cleanup-handoff-',
                                dir=os.environ.get('RUNNER_TEMP'))).resolve()
    journal=None
    env=dict(os.environ,TMPDIR=str(root))
    child=subprocess.Popen([sys.executable,'-u','-c',DRIVER,str(ROOT)],env=env,
                           stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    def emit(snapshot):
        print(json.dumps({'cleanup_handoff':snapshot,
                          'journal_path':str(custody/'cleanup.sqlite')},sort_keys=True),flush=True)
    def docker(*args):
        return subprocess.run(['docker',*args],check=True,capture_output=True,
                              text=True,timeout=15).stdout.strip()
    try:
        if not select.select([child.stdout],[],[],180)[0]:
            raise RuntimeError('Abrupt-stop readiness timeout')
        owned=json.loads(child.stdout.readline()).get('ready')
        if not owned:raise RuntimeError('No owned container readiness')
        name=owned['name'];stage=Path(owned['stage'])
        if (re.fullmatch(r'nexus-acceptance-[0-9a-f]{32}',name) is None
                or stage.name!='source' or stage.parent.parent.resolve()!=root
                or not stage.parent.name.startswith('nexus-isolated-')
                or stage.is_symlink() or stage.parent.is_symlink()):
            raise RuntimeError('Supervisor scope mismatch; no removal authorized')
        info=json.loads(docker('inspect',name))[0]
        if not any(m.get('Source')==str(stage) and m.get('Destination')=='/sandbox'
                   for m in info['Mounts']):
            raise RuntimeError('Owned mount mismatch')
        plan={'run_id':os.environ.get('GITHUB_RUN_ID','local')+':'+
                      os.environ.get('GITHUB_RUN_ATTEMPT','1')+':'+root.name,
              'source_sha':os.environ.get('SOURCE_SHA','UNVERIFIED'),
              'steps':[{'action':'STOP_RUNNER','target':'pid:'+str(child.pid)},
                       {'action':'REMOVE_CONTAINER','target':name},
                       {'action':'REMOVE_STAGING','target':str(stage.parent)},
                       {'action':'REMOVE_NAMESPACE','target':str(root)}]}
        journal=Journal.create(custody/'cleanup.sqlite',plan)
        emit(journal.snapshot())
        def stop():
            child.kill();child.wait(timeout=5)
        journal.execute('STOP_RUNNER',stop,
                        lambda:child.returncode==-signal.SIGKILL,emit)
        before=json.loads(docker('inspect',name))[0]['State']['Running']
        staged_before=stage.parent.exists()
        def absent():
            return not docker('ps','--all','--quiet','--filter','name=^/'+name+'$')
        journal.execute('REMOVE_CONTAINER',lambda:docker('rm','--force',name),absent,emit)
        journal.execute('REMOVE_STAGING',lambda:shutil.rmtree(stage.parent),
                        lambda:not stage.parent.exists(),emit)
        journal.execute('REMOVE_NAMESPACE',root.rmdir,lambda:not root.exists(),emit)
        out,err=child.communicate(timeout=10)
        # Reopen the retained journal through a fresh handle after resources go.
        handoff=Journal(custody/'cleanup.sqlite',plan).snapshot()
        passed=(child.returncode==-signal.SIGKILL and before and staged_before
                and absent() and not stage.parent.exists() and not out.strip()
                and handoff['next_permitted_step']=='COMPLETE')
        print(json.dumps({'case_id':'REAL-DOCKER-RUNNER-SIGKILL-SUPERVISOR',
            'status':'PASSED' if passed else 'FAILED','signal_observed':child.returncode==-signal.SIGKILL,
            'orphan_running_before_cleanup':before,'staging_present_before_cleanup':staged_before,
            'container_absent_after_cleanup':absent(),'staging_absent_after_cleanup':not stage.parent.exists(),
            'runner_report_absent':not out.strip(),'source_sha':os.environ.get('SOURCE_SHA'),
            'cleanup_handoff':handoff,'journal_path':str(custody/'cleanup.sqlite'),
            'limits':['Journal survives owned worker and staging loss on the same host only',
                      'No automatic retry, remote ownership, host-loss recovery or retention deletion',
                      'Initialization before resource enrollment is outside this handoff']},sort_keys=True))
        return 0 if passed else 2
    finally:
        # Do not silently delete retained staging or blindly repeat an uncertain
        # operation. A failed run preserves the handoff for explicit inspection.
        if journal is not None:
            emit(journal.snapshot())
        elif child.poll() is None:
            print(json.dumps({'cleanup_enrollment':'BLOCKED','namespace':str(root),
                              'runner_pid':child.pid,'next_step':'Inspect ownership before cleanup'}),flush=True)
