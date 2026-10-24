"""Reject workflow additions or byte changes absent an explicit policy update.

This checks committed files only, not GitHub hooks/settings or event delivery.
Policy changes still require trusted review; it is not tamper-proof authority.
"""
import hashlib
import json
from pathlib import Path


def verify(root, policy):
    folder=Path(root)/'.github/workflows'
    entries=list(folder.iterdir())
    if any(not p.is_file() or p.is_symlink() for p in entries):
        raise ValueError('Unexpected workflow entry type')
    actual={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in entries}
    if actual != policy:
        raise ValueError('Workflow inventory differs from reviewed trigger/network policy')
    return sorted(actual)


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    names=verify(root,json.loads((root/'tools/workflow_policy.json').read_text()))
    print(json.dumps({'workflow_inventory':'MATCHED','files':names,
                      'scope':'committed workflow bytes only; settings/hooks not inspected'}))
