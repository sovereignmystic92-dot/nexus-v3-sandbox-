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


def run():
    from real_container_stop_probe import DRIVER, ROOT
    with tempfile.TemporaryDirectory(prefix='nexus-supervisor-') as namespace:
        root=Path(namespace).resolve()
        env=dict(os.environ,TMPDIR=str(root))
        child=subprocess.Popen([sys.executable,'-u','-c',DRIVER,str(ROOT)],env=env,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        name=None
        try:
            if not select.select([child.stdout],[],[],180)[0]:
                raise RuntimeError('Abrupt-stop readiness timeout')
            owned=json.loads(child.stdout.readline()).get('ready')
            if not owned:raise RuntimeError('No owned container readiness')
            candidate=owned['name']
            stage=Path(owned['stage'])
            if (re.fullmatch(r'nexus-acceptance-[0-9a-f]{32}',candidate) is None
                    or stage.name!='source' or stage.parent.parent.resolve()!=root
                    or not stage.parent.name.startswith('nexus-isolated-')
                    or stage.is_symlink() or stage.parent.is_symlink()):
                raise RuntimeError('Supervisor scope mismatch; no removal authorized')
            name=candidate
            def docker(*args):
                return subprocess.run(['docker',*args],check=True,capture_output=True,
                                      text=True,timeout=15).stdout.strip()
            info=json.loads(docker('inspect',name))[0]
            if not any(m.get('Source')==str(stage) and m.get('Destination')=='/sandbox'
                       for m in info['Mounts']):
                raise RuntimeError('Owned mount mismatch')
            child.kill();child.wait(timeout=5)
            before=json.loads(docker('inspect',name))[0]['State']['Running']
            staged_before=stage.parent.exists()
            docker('rm','--force',name)
            shutil.rmtree(stage.parent)
            absent=not docker('ps','--all','--quiet','--filter','name=^/'+name+'$')
            out,err=child.communicate(timeout=10)
            passed=(child.returncode==-signal.SIGKILL and before and staged_before
                    and absent and not stage.parent.exists() and not out.strip())
            print(json.dumps({'case_id':'REAL-DOCKER-RUNNER-SIGKILL-SUPERVISOR',
                'status':'PASSED' if passed else 'FAILED','signal_observed':child.returncode==-signal.SIGKILL,
                'orphan_running_before_cleanup':before,'staging_present_before_cleanup':staged_before,
                'container_absent_after_cleanup':absent,'staging_absent_after_cleanup':not stage.parent.exists(),
                'runner_report_absent':not out.strip(),'source_sha':os.environ.get('SOURCE_SHA'),
                'limits':['Supervisor and Docker host survive; not total host loss',
                          'Explicit foreground test supervisor, not an installed crash-recovery service',
                          'No retention expiry or checkpoint closure']},sort_keys=True))
            return 0 if passed else 2
        finally:
            if child.poll() is None:child.kill();child.wait(timeout=5)
            if name:
                subprocess.run(['docker','rm','--force',name],capture_output=True,timeout=15)
