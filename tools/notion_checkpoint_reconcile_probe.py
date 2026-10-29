"""Observe one historical checkpoint with current code; no append path."""
import json
import os
from pathlib import Path
import re
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from notion_checkpoint_write_probe import probe
from nexus_sandbox.notion_checkpoint_api import NotionRequest

AUDIT_ID='4018c067daa48122b82ec2ae8067d021'
TARGET_RUN_ID='40781386183'
TARGET_SOURCE='1ff5dbffbcd900687b4477490ded37827b0cc892'
TARGET_CHECKPOINT_SHA256='2ad2aeed75e89de7a22c0374e7da205e0523c26b1b5d8c87fc88a7a0c0bf0288'


def reconcile(request,execution_source):
    if type(execution_source) is not str or re.fullmatch(r'[0-9a-f]{40}',execution_source) is None:
        raise ValueError('Execution source binding required')
    reads=0
    def read_only(method,path,payload):
        nonlocal reads
        if method!='GET' or payload is not None:
            raise ValueError('Reconciliation is read-only')
        reads+=1
        if reads>11:raise ValueError('Read budget exhausted')
        return request(method,path,payload)
    result=probe(read_only,TARGET_RUN_ID,TARGET_SOURCE,allow_write=False)
    if type(result.get('writes_attempted')) is not int or result['writes_attempted']!=0:
        raise ValueError('Unexpected write accounting')
    if result.get('checkpoint_sha256')!=TARGET_CHECKPOINT_SHA256:
        raise ValueError('Historical checkpoint recipe changed')
    return dict(result,execution_mode='OBSERVE_ONLY_RECONCILIATION',
                execution_source_revision=execution_source,
                target_run_id=TARGET_RUN_ID,target_binding_source_revision=TARGET_SOURCE)


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
        result=reconcile(paced,source)
    except Exception:
        print('{"result":"BLOCKED","reason":"RECONCILIATION_UNAVAILABLE"}');return 2
    print(json.dumps(result,sort_keys=True))
    return 0 if result['result'].startswith('VERIFIED') else 2


if __name__=='__main__':raise SystemExit(main())

