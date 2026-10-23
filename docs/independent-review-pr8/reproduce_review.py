"""Run independent local reproduction; no live or Docker execution."""
import hashlib,json,os,pathlib,platform,shutil,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parent
env=dict(os.environ,PYTHONPATH='src:tests/unit')
names=('test_history_loss_blocks_replacement_before_transport','test_history_loss_requires_trusted_restore_even_for_original','test_latest_receipt_event_divergence_blocks_before_transport','test_lost_first_verification_cannot_reanchor_to_later_replacement','test_complete_legacy_history_backfills_anchor_before_read','test_anchor_failure_rolls_back_verification_then_reconciles','test_orphaned_anchor_and_events_block_before_transport')
critical=['test_cortex_adapter.CortexAdapterTests.'+name for name in names]
commands=[[sys.executable,'tools/validate.py','--output','reviewer-validation.json'],[sys.executable,'-m','unittest','discover','-s','tests/unit','-v'],[sys.executable,'-m','unittest','-v',*critical],[sys.executable,'reviewer_probes.py']]
results={'python':sys.version,'platform':platform.platform(),'cwd':str(ROOT),'revision':'4b396f64b1b1174a9f3da0366a82a530453067e9','runs':[]}
for index,cmd in enumerate(commands):
    run=subprocess.run(cmd,cwd=ROOT,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    output='reviewer-run-'+str(index)+'.txt';(ROOT/output).write_text(run.stdout)
    results['runs'].append({'command':cmd,'environment_override':{'PYTHONPATH':'src:tests/unit'},'returncode':run.returncode,'output':output})
    print(index,run.returncode,run.stdout[-150:])
with tempfile.TemporaryDirectory(prefix='nexus-independent-baseline-') as temp:
    temp=pathlib.Path(temp);shutil.copytree(ROOT/'src',temp/'src');shutil.copytree(ROOT/'tests',temp/'tests')
    shutil.copyfile(ROOT/'baseline-cortex-adapter.py',temp/'src/nexus_sandbox/cortex_adapter.py')
    cmd=[sys.executable,'-m','unittest','-v',*critical]
    run=subprocess.run(cmd,cwd=temp,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (ROOT/'reviewer-baseline-output.txt').write_text(run.stdout)
    results['baseline_contrast']={'baseline_adapter_revision':'ae22d1ccc1f1dc731fbca250a06475f6830d1025','other_source_and_tests_revision':results['revision'],'command':cmd,'returncode':run.returncode,'output':'reviewer-baseline-output.txt','temporary_directory_deleted_on_exit':True}
    print('baseline contrast',run.returncode,run.stdout[-150:])
(ROOT/'reviewer-commands-results.json').write_text(json.dumps(results,indent=2)+'\n')
