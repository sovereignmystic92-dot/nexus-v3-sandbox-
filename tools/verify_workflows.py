"""Reject workflow additions or byte changes absent an explicit policy update.

This checks committed files only, not GitHub hooks/settings or event delivery.
Policy changes still require trusted review; it is not tamper-proof authority.
"""
import hashlib

# CI-only source-level credential routing contract; host exclusion remains unproven.
import re

PROVIDER_SECRETS = {
    'gemini-smoke.yml': ('gemini-pilot', {'GEMINI_PILOT_API_KEY'}),
    'notion-audit-access-probe.yml': ('notion-sandbox', {'NOTION_SANDBOX_TOKEN'}),
    'notion-boundary-probe.yml': ('notion-sandbox', {'NOTION_SANDBOX_TOKEN', 'NOTION_SANDBOX_ROOT_ID', 'NOTION_SANDBOX_DENIED_PAGE_ID'}),
    'notion-checkpoint-reconcile-probe.yml': ('notion-sandbox', {'NOTION_SANDBOX_TOKEN'}),
    'notion-checkpoint-write-probe.yml': ('notion-sandbox', {'NOTION_SANDBOX_TOKEN'}),
    'notion-identity-probe.yml': ('notion-sandbox', {'NOTION_SANDBOX_TOKEN'}),
    'notion-read-probe.yml': ('notion-sandbox', {'NOTION_SANDBOX_TOKEN', 'NOTION_SANDBOX_ROOT_ID'}),
}
ENVIRONMENT_ONLY = {'cp04-environment-enforcement-probe.yml': 'notion-sandbox'}

def verify_credential_routing(root):
    folder = Path(root) / '.github/workflows'
    for path in folder.iterdir():
        source = path.read_text()
        if not re.search(r'(?m)^permissions:\s*\{\}\s*$', source):
            raise ValueError('Workflow lacks empty permissions: ' + path.name)
        actual_secrets = set(re.findall(r'\$\{\{\s*secrets\.([A-Za-z_][A-Za-z0-9_]*)', source))
        actual_environments = set(re.findall(r'(?m)^\s*environment:\s*([A-Za-z0-9_-]+)\s*$', source))
        expected_environment, expected_secrets = PROVIDER_SECRETS.get(path.name, (ENVIRONMENT_ONLY.get(path.name), set()))
        if actual_secrets != expected_secrets or actual_environments != ({expected_environment} if expected_environment else set()):
            raise ValueError('Credential routing differs from reviewed contract: ' + path.name)
        if re.search(r'\$\{\{\s*github\.token\b', source, re.I):
            raise ValueError('Explicit github.token reference: ' + path.name)
    return True

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
    verify_credential_routing(root)
    print(json.dumps({'workflow_inventory':'MATCHED','files':names,
                      'scope':'committed workflow bytes only; settings/hooks not inspected'}))
