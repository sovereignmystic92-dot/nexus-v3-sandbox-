"""Alternative read-only Cortex module_list observation for a host callback.

A module_list observation is NOT authentication or a durable checkpoint.
Require an exact, unique result and an exhausted provider result page.
"""
import json
from collections.abc import Mapping


def observe_cortex_module_list(*, module_id, exact_name, invoke):
    if (not isinstance(module_id, str) or not module_id.startswith("module_")
            or not isinstance(exact_name, str) or not exact_name
            or not callable(invoke)):
        raise ValueError("Exact Cortex fixture and callback required")
    raw = invoke("module_list", {"q": exact_name, "permission": "module.view", "limit": 100})
    if not isinstance(raw, Mapping) or raw.get("isError") is True:
        raise ValueError("Cortex module list failed")
    data = raw.get("structuredContent")
    if data is None:
        body = raw.get("text")
        if not isinstance(body, str):
            raise ValueError("Cortex module list response missing")
        try:
            data = json.loads(body)
        except (ValueError, TypeError) as exc:
            raise ValueError("Cortex module list response malformed") from exc
    if (not isinstance(data, Mapping) or data.get("has_more") is not False
            or not isinstance(data.get("data"), list)):
        raise ValueError("Cortex module inventory incomplete")
    exact = [m for m in data["data"] if isinstance(m, Mapping)
             and m.get("name") == exact_name]
    if len(exact) != 1:
        raise ValueError("Cortex module identity ambiguous or absent")
    m = exact[0]
    if (m.get("id") != module_id or type(m.get("version")) is not int
            or m["version"] < 1 or not isinstance(m.get("content"), str)
            or not isinstance(m.get("dependencies"), list)
            or not all(isinstance(d, str) for d in m["dependencies"])
            or m.get("archived") is not False):
        raise ValueError("Cortex module identity or content invalid")
    return ({
        "module_id": m["id"], "name": exact_name,
        "version": m["version"], "content": m["content"],
        "dependencies": list(m["dependencies"]),
    }, {"authenticated": False, "complete_inventory": False})
