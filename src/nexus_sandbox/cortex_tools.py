"""Read-only legacy callback bridge; bound transport required for updates.

Historical probes that used unbound create/update now fail before invoking the
provider. This does not restrict access to tools outside this Python bridge.
"""

import json
from .cortex_adapter import Module


class ToolFailure(RuntimeError):
    pass


class CortexToolTransport:
    def __init__(self, invoke):
        self.invoke = invoke

    def get(self, name):
        result = self.invoke("context_get", {"name": name})
        blocks = [b["text"] for b in result.get("content", []) if b.get("type") == "text"]
        if result.get("isError"):
            # This exact combination was observed for the synthetic C04 missing
            # probe. INVALID_ARGUMENT alone must never mean absent.
            if (result.get("structuredContent", {}).get("error_code") == "INVALID_ARGUMENT"
                    and blocks == ["module matching query does not exist"]):
                return None
            raise ToolFailure("Cortex read failed; absence not established")
        try:
            data = result.get("structuredContent") or json.loads("\n".join(blocks))
            if (type(data["version"]) is not int or not isinstance(data["dependencies"], list)
                    or data.get("archived") is not False):
                raise ValueError()
            return Module(data["id"], data["name"], data["version"],
                          data["content"], tuple(data["dependencies"]))
        except Exception:
            raise ToolFailure("Incomplete Cortex module observation") from None

    def _write(self, tool, name, content, dependencies):
        raise ToolFailure("Unbound provider writes disabled; use a verified bound fixture transport")

    def create(self, name, content, dependencies):
        self._write("context_create", name, content, dependencies)

    def update(self, name, content, dependencies):
        # Omits owner/parent/permissions/default_assignee fields entirely.
        self._write("context_update", name, content, dependencies)

