"""Credential-free host preflight against the actual Git parent/base revision."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from nexus_sandbox.checkpoint_ledger import validate_transition


def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args],text=True,timeout=30)


def main():
    source = os.environ.get('SOURCE_SHA','')
    if re.fullmatch('[0-9a-f]{40}',source) is None or git('rev-parse','HEAD').strip() != source:
        raise ValueError('Exact checked-out revision required')
    event = os.environ.get('SOURCE_EVENT')
    if event == 'pull_request':
        base = os.environ.get('PR_BASE_SHA','')
    elif event == 'push':
        parents = [line.split()[1] for line in git('cat-file','-p','HEAD').split('\n\n',1)[0].splitlines()
                   if line.startswith('parent ')]
        if not parents:
            raise ValueError('Missing prior accepted source revision')
        base = parents[0]
    else:
        raise ValueError('Unsupported source event')
    if re.fullmatch('[0-9a-f]{40}',base) is None:
        raise ValueError('Exact GitHub base required')
    # Source fetch is on the host, before the network-disabled test container.
    subprocess.run(['git','-C',str(ROOT),'-c','credential.helper=','fetch','--depth=1',
                    'https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-.git',base],
                   check=True,capture_output=True,text=True,timeout=60)
    path = 'tools/recovery_ledger.json'
    exists = git('ls-tree',base,'--',path).strip()
    baseline = json.loads(git('show',base+':'+path)) if exists else {'schema_version':1,'records':[],'latest':None}
    candidate = json.loads((ROOT/path).read_text())
    latest = validate_transition(baseline,candidate)
    print(json.dumps({'checkpoint_ledger':'MATCHED_APPEND_ONLY_BASE','base_sha':base,
                      'candidate_sha':source,'latest':latest,'initialized':latest is not None}))


if __name__ == '__main__':
    main()
