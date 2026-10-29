"""Host-only exact-source preflight ordering; not provider-control proof."""
from pathlib import Path
import json

def verify(root):
    folder=Path(root)/'.github/workflows'
    names=('gemini-smoke.yml','notion-read-probe.yml','notion-identity-probe.yml',
           'notion-boundary-probe.yml','notion-audit-access-probe.yml',
           'notion-checkpoint-write-probe.yml','notion-checkpoint-reconcile-probe.yml')
    for name in names:
        source=(folder/name).read_text()
        if source.index('Approval policy preflight') >= source.index('${{ secrets.'):
            raise ValueError('Preflight must precede credential use')
        if '--workflow '+name not in source:
            raise ValueError('Preflight workflow binding missing')
    return list(names)

if __name__=='__main__':
    print(json.dumps({'preflight_source_coverage':'MATCHED','workflows':verify(Path(__file__).resolve().parents[1]),
                      'scope':'committed source order only, not live enforcement'}))
