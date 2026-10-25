"""Opt-in existing-fixture transport with pinned root and ownership checks.

Owner metadata is not authenticated caller/account identity. No provider CAS,
credential restriction or automatic enrollment; CP05 is not passed by this alone.
"""
from dataclasses import dataclass
import hashlib
import json
import re
from types import MappingProxyType
from .cortex_adapter import MARKER, Module
from .cortex_tools import ToolFailure


@dataclass(frozen=True)
class FixtureBinding:
    name: str
    module_id: str
    owner: str
    parent: str | None


class BoundCortexToolTransport:
    def __init__(self, invoke, bindings, root_name, root_version, root_content_sha256, root_dependencies=()):
        entries=tuple(bindings)
        if (not entries or any(type(b) is not FixtureBinding or
                not isinstance(b.name,str) or not b.name.startswith('Nexus Sandbox ')
                or not isinstance(b.module_id,str) or not b.module_id
                or not isinstance(b.owner,str) or not b.owner or
                (b.parent is not None and not isinstance(b.parent,str)) for b in entries)
                or len({b.name for b in entries})!=len(entries)
                or len({b.module_id for b in entries})!=len(entries)
                or root_name not in {b.name for b in entries}
                or type(root_dependencies) is not tuple
                or any(not isinstance(d,str) or d not in {b.name for b in entries} for d in root_dependencies)
                or len(set(root_dependencies))!=len(root_dependencies)
                or type(root_version) is not int or root_version<1
                or not isinstance(root_content_sha256,str)
                or re.fullmatch('[0-9a-f]{64}',root_content_sha256) is None):
            raise ValueError('Explicit immutable synthetic fixture and root bindings required')
        self.bindings=MappingProxyType({b.name:b for b in entries})
        self.root_name,self.root_version,self.root_hash=root_name,root_version,root_content_sha256
        self.root_dependencies=root_dependencies
        self._invoke=invoke

    def _bound(self,name):
        if not isinstance(name,str) or name not in self.bindings:
            raise ToolFailure('Destination is outside the pinned fixture scope')
        return self.bindings[name]

    def _decode(self,result,name):
        if not isinstance(result,dict) or result.get('isError'):
            raise ToolFailure('Bound fixture observation unavailable; no mutation permitted')
        try:
            data=result.get('structuredContent')
            if data is None:
                blocks=result.get('content',[])
                if (type(blocks) is not list or any(type(b) is not dict for b in blocks)):
                    raise ValueError()
                data=json.loads('\n'.join(b['text'] for b in blocks if b.get('type')=='text'))
            if type(data) is not dict:
                raise ValueError()
            binding=self._bound(name)
            if (data['id']!=binding.module_id or data['name']!=binding.name
                    or data['owner']!=binding.owner or data['parent']!=binding.parent
                    or data['archived'] is not False or type(data['version']) is not int
                    or data['version']<1 or not isinstance(data['content'],str)
                    or not data['content'].startswith(MARKER)
                    or type(data['dependencies']) is not list
                    or any(not isinstance(d,str) or d not in self.bindings for d in data['dependencies'])
                    or len(set(data['dependencies']))!=len(data['dependencies'])):
                raise ValueError()
            return data
        except (KeyError,ValueError,TypeError):
            raise ToolFailure('Fixture identity/owner/parent/synthetic marker mismatch') from None

    def _read(self,name):
        self._bound(name)
        return self._decode(self._invoke('context_get',{'name':name}),name)

    def _root(self):
        data=self._read(self.root_name)
        if (data['version']!=self.root_version or tuple(data['dependencies'])!=self.root_dependencies or
                hashlib.sha256(data['content'].encode()).hexdigest()!=self.root_hash):
            raise ToolFailure('Pinned root revision or content changed; hold for reassessment')
        return data

    def get(self,name):
        self._bound(name)
        root=self._root()
        d=root if name==self.root_name else self._read(name)
        return Module(d['id'],d['name'],d['version'],d['content'],tuple(d['dependencies']))

    def create(self,*args):
        raise ToolFailure('Unenrolled fixture creation is disabled; no provider call made')

    def update(self,name,content,dependencies):
        self._bound(name)
        if (name==self.root_name or not isinstance(content,str) or not content.startswith(MARKER)
                or type(dependencies) is not tuple or any(not isinstance(d,str) for d in dependencies)
                or len(set(dependencies))!=len(dependencies)
                or name in dependencies or any(d not in self.bindings for d in dependencies)):
            raise ToolFailure('Update outside exact existing-fixture scope')
        self._root()
        before=self._read(name)
        for dependency in dependencies:
            self._read(dependency)
        # Sequential preflight is not atomic with this provider mutation.
        result=self._invoke('context_update',{'name':name,'content':content,'dependencies':list(dependencies)})
        after=self._decode(result,name)
        if (after['version']!=before['version']+1 or after['content']!=content
                or after['dependencies']!=list(dependencies)):
            raise ToolFailure('Write acknowledgment differs; reconcile without blind retry')

