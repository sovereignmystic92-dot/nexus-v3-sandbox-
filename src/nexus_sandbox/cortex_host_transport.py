"""Host-injected Cortex transport: no network client, credentials, or implicit writes.

Host callbacks must raise on read failures, never return None for an outage.
The CortexAdapter owns durable intent, reconciliation and independent readback.
"""
from .cortex_adapter import Module


class CortexHostTransport:
    def __init__(self, *, read, create, update):
        if not all(callable(fn) for fn in (read, create, update)):
            raise TypeError("Explicit callable host bindings required")
        self._read = read
        self._create = create
        self._update = update

    def get(self, name: str) -> Module | None:
        result = self._read(name)
        if result is None:
            return None
        if type(result) is not dict:
            raise ValueError("Host read must return a complete module mapping")
        dependencies = result.get("dependencies")
        if type(dependencies) is not list or not all(type(x) is str for x in dependencies):
            raise ValueError("Malformed host dependencies")
        module = Module(
            id=result["id"], name=result["name"], version=result["version"],
            content=result["content"], dependencies=tuple(dependencies))
        return module

    def create(self, name: str, content: str, dependencies: tuple[str, ...]):
        return self._create(name, content, list(dependencies))

    def update(self, name: str, content: str, dependencies: tuple[str, ...]):
        return self._update(name, content, list(dependencies))
