"""Real signals to an owned runner process with a fake Docker backend.

These tests exercise actual main/finally and staging removal, not real containers
or host shutdown. No external process or provider is signalled.
"""
import json
from pathlib import Path
import select
import signal
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
DRIVER = r'''
import json,os,sys,time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,sys.argv[1]+'/tools')
import run_isolated as r
os.environ.update(SOURCE_SHA='a'*40,GITHUB_RETENTION_DAYS='1')
r.shutil.which=lambda name:'/fake/docker'
calls=[]
def command(args,**kwargs):
    calls.append(args[:3])
    if args[0]=='git':return 'a'*40
    if args[:3]==['docker','image','inspect']:return json.dumps([{'Id':'fake-image'}])
    if args[:2]==['docker','inspect']:return '[{}]'
    return ''
r.command=command
r.validate_container=lambda *args:{'fake_backend':True}
def stage(path):
    path.mkdir();(path/'synthetic.txt').write_text('disposable')
    r.staging_path=str(path.parent)
    return {}
r.stage_sources=stage
def execute(args,**kwargs):
    if args[0]=='python3':
        return SimpleNamespace(returncode=0,stdout='{"checkpoint_ledger":"MATCHED_APPEND_ONLY_BASE"}')
    print('READY '+r.staging_path,flush=True)
    time.sleep(30)
r.subprocess.run=execute
code=r.main()
print(json.dumps({'calls':calls}),flush=True)
sys.exit(code)
'''


class RunnerStopTests(unittest.TestCase):
    def check_stop(self, stop_signal):
        with subprocess.Popen([sys.executable,'-u','-c',DRIVER,str(ROOT)],
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) as child:
            try:
                self.assertTrue(select.select([child.stdout],[],[],10)[0])
                ready=child.stdout.readline().strip()
                self.assertTrue(ready.startswith('READY '))
                staging=Path(ready.removeprefix('READY '))
                self.assertTrue(staging.exists())
                child.send_signal(stop_signal)
                out,err=child.communicate(timeout=10)
                self.assertEqual(child.returncode,2,err)
                report,calls=[json.loads(line) for line in out.splitlines()]
                self.assertEqual(report['isolated_run_status'],'BLOCKED')
                self.assertIn(signal.Signals(stop_signal).name,report['blocker'])
                self.assertTrue(report['container_removed'])
                self.assertTrue(report['source_staging_removed'])
                self.assertFalse(staging.exists())
                self.assertIn(['docker','rm','--force'],calls['calls'])
            finally:
                if child.poll() is None:
                    child.kill();child.wait(timeout=5)

    def test_sigterm_cleans_real_staging_and_reports_blocked(self):
        self.check_stop(signal.SIGTERM)

    def test_sigint_cleans_real_staging_and_reports_blocked(self):
        self.check_stop(signal.SIGINT)
