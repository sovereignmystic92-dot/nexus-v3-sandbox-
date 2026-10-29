"""Fixed saved-checkpoint observation -> read-only resume decision; no executor."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from nexus_sandbox.audit_checkpoint_transport import AuditCheckpointTransport
from nexus_sandbox.checkpoint_json import decode
from nexus_sandbox.notion_checkpoint_api import NotionCheckpointAPI,NotionRequest,request_error_evidence
from nexus_sandbox.processing_pipeline import STAGES
from nexus_sandbox.resume_decision import decide_resume

AUDIT_ID='4018c067daa48122b82ec2ae8067d021'
TARGET_RUN_ID='40862662915'
TARGET_SOURCE='d55ecbe22b9a34ab0c9498cc5f7014aac20e77b2'
TARGET_SHA256='7409a0f2aae701d8d1c4cbce51426d96f455ec989f8e966ea3243696bdca17a8'


def observe_plan(request,execution_source):
    if type(execution_source) is not str or re.fullmatch(r'[0-9a-f]{40}',execution_source) is None:
        raise ValueError('Execution source binding required')
    job='NXS-LIVE-CHECKPOINT-'+TARGET_RUN_ID
    binding=dict(run_id=job,source_id='github-actions:'+TARGET_RUN_ID,
        source_sha256=hashlib.sha256(('checkpoint-write-probe:'+TARGET_RUN_ID).encode()).hexdigest(),
        destination_id=AUDIT_ID,policy_revision='bounded-live-checkpoint-test-20261028-v1',
        code_revision=TARGET_SOURCE,schema_version=1)
    reads=0
    def read_only(method,path,payload):
        nonlocal reads
        if method!='GET' or payload is not None:raise ValueError('Read-only handoff')
        reads+=1
        if reads>11:raise ValueError('Read budget exhausted')
        return request(method,path,payload)
    def no_append(*args):raise ValueError('No append capability in handoff')
    summary=dict(marker=job,destination=AUDIT_ID,target_binding_source_revision=TARGET_SOURCE,
        expected_checkpoint_sha256=TARGET_SHA256,execution_source_revision=execution_source,
        provider_writes=0,writes_attempted=0,automatic_execution=False,
        executor_callbacks_invoked=0,execution_authority='NOT_ESTABLISHED',
        bridge_activation='INACTIVE',cp09='NOT_PROVEN')
    try:
        api=NotionCheckpointAPI(AUDIT_ID,read_only,write_enabled=False)
        transport=AuditCheckpointTransport(AUDIT_ID,binding,api.fetch_page,no_append)
        text=transport.read(job)
        if hashlib.sha256(text.encode()).hexdigest()!=TARGET_SHA256:
            raise ValueError('Checkpoint snapshot drift')
        state=decode(text,binding)
        # Complete inventory follows validated adapter/transport read, not a CLI flag.
        # Read permission does not prove current execution authority or fencing.
        decision=decide_resume(text,binding,inventory_complete=True,authority_verified=False)
        completed=[receipt.stage for receipt in state['receipts']]
        observed_next=state['pending'] or (STAGES[len(completed)] if len(completed)<len(STAGES) else None)
        return dict(summary,result='VERIFIED_OBSERVATION_EXECUTION_BLOCKED',
            checkpoint_sha256=TARGET_SHA256,reads=reads,observation_error=None,
            observed_completed_stages=completed,observed_pending_stage=state['pending'],
            observed_next_stage=observed_next,
            resume_decision=dict(status=decision.status,next_action=decision.next_action,
                pending=decision.pending,reason=decision.reason))
    except Exception as error:
        return dict(summary,result='BLOCKED',reads=reads,
            observation_error=request_error_evidence(error),observed_next_stage=None,
            resume_decision=None)


def main():
    if (os.environ.get('GITHUB_REPOSITORY')!='sovereignmystic92-dot/nexus-v3-sandbox-'
            or os.environ.get('GITHUB_REF')!='refs/heads/main'
            or os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch'
            or os.environ.get('NOTION_CHECKPOINT_RECONCILE_CONFIRMED')!='true'):
        print('{"result":"SKIPPED"}');return 2
    try:
        source=os.environ.get('GITHUB_SHA','')
        if re.fullmatch(r'[0-9a-f]{40}',source) is None:raise ValueError('Source required')
        client=NotionRequest(AUDIT_ID,os.environ.pop('NOTION_SANDBOX_TOKEN',''),
                            '2022-06-28',write_enabled=False)
        def paced(method,path,payload):
            time.sleep(0.4)
            return client(method,path,payload)
        result=observe_plan(paced,source)
    except Exception:
        print('{"result":"BLOCKED","reason":"READ_ONLY_HANDOFF_UNAVAILABLE"}');return 2
    print(json.dumps(result,sort_keys=True))
    # Success means observation/plan emission, never permission to execute.
    return 0 if result['result']=='VERIFIED_OBSERVATION_EXECUTION_BLOCKED' else 2


if __name__=='__main__':raise SystemExit(main())

