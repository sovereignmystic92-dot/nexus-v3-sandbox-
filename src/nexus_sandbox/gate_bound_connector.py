"""Read-only Cortex connector call bridge for the CP02 host preflight.

The provider exposes context_get(name) and context_access(name). Neither by
itself attests the currently executing principal. A separate provider-authenticated
identity_exact callback is REQUIRED and cannot be replaced by a configured name.
The host must ensure all three calls use the same authenticated session.
"""
import json


class CortexConnectorReadHost:
    def __init__(self, *, invoke, identity_exact, module_names):
        if not callable(invoke) or not callable(identity_exact):
            raise ValueError("Authenticated invoke and identity reader required")
        if (type(module_names) is not dict or not module_names or
                any(type(k) is not str or not k.startswith("synthetic:") or
                    type(v) is not tuple or len(v) != 2 or\n                    type(v[0]) is not str or not v[0].startswith("Nexus Sandbox ") or\n                    type(v[1]) is not str or not v[1].startswith("module_")
                    for k, v in module_names.items()) or
                len(set(module_names.values())) != len(module_names)):
            raise ValueError("Pinned synthetic Cortex module names required")
        self._invoke = invoke
        self._identity_exact = identity_exact
        self._names = dict(module_names)

    def _name(self, target):
        if type(target) is not str or target not in self._names:
            raise ValueError("Read outside pinned synthetic module scope")
        return self._names[target][0]

    def _call(self, method, target):
        # No write or other tool method is accepted.
        if method not in ("context_access", "context_get"):
            raise ValueError("Read-only connector method required")
        raw = self._invoke(method, {"name": self._name(target)})
        if type(raw) is not dict or raw.get("isError"):
            raise ValueError("Provider response unavailable")
        if "structuredContent" in raw:
            data = raw["structuredContent"]
        else:
            content = raw.get("content")
            if (type(content) is not list or len(content) != 1
                    or type(content[0]) is not dict
                    or content[0].get("type") != "text"
                    or type(content[0].get("text")) is not str):
                raise ValueError("Malformed provider envelope")
            data = json.loads(content[0]["text"])
        if type(data) is not dict:
            raise ValueError("Malformed provider result")
        return data

    def identity_exact(self):
        identity = self._identity_exact()
        if (type(identity) is not dict or set(identity) !=
                {"provider", "principal", "authenticated"} or
                type(identity["principal"]) is not str or
                not identity["principal"] or
                type(identity["authenticated"]) is not bool or
                identity["authenticated"] is not True or
                identity["provider"] != "CORTEX"):
            raise ValueError("Provider identity not attested")
        return dict(identity)

    def permissions_exact(self, target):
        self._name(target)
        principal = self.identity_exact()["principal"]
        access = self._call("context_access", target)
        if (set(access) != {"permissions", "is_owner"} or
                type(access["permissions"]) is not list or
                any(type(s) is not str for s in access["permissions"]) or
                len(set(access["permissions"])) != len(access["permissions"]) or
                type(access["is_owner"]) is not bool):
            raise ValueError("Incomplete provider access report")
        return {"provider": "CORTEX", "target": target,
                "principal": principal, "permissions": access["permissions"],
                "complete": True}

    def read_exact(self, target):
        self._name(target)
        principal = self.identity_exact()["principal"]
        data = self._call("context_get", target)
        # Match the documented Cortex GET /v1/modules/{name} representation.
        # Never manufacture a version or assume a missing field means complete.
        required = {"id", "name", "content", "version", "archived",
                    "dependencies", "owner", "default_assignee", "parent",
                    "inherit_permissions", "created_at", "updated_at"}
        if set(data) != required:
            raise ValueError("Incomplete provider module representation")
        if (data["id"] != self._names[target][1] or
                data["name"] != self._name(target) or
                type(data["version"]) is not int or data["version"] < 1 or
                type(data["content"]) is not str or
                type(data["archived"]) is not bool or data["archived"] or
                type(data["dependencies"]) is not list or
                any(type(item) is not str for item in data["dependencies"]) or
                type(data["owner"]) is not str or not data["owner"] or
                type(data["inherit_permissions"]) is not bool or
                any(type(data[k]) is not str or not data[k]
                    for k in ("created_at", "updated_at"))):
            raise ValueError("Mismatched or incomplete provider module")
        return {"provider": "CORTEX", "principal": principal, "target": target,
                "revision": str(data["version"]), "complete": True,
                "truncated": False}
