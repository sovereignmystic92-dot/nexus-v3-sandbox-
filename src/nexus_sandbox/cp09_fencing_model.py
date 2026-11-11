"""Synthetic atomic fencing model. Not a Cortex provider adapter."""
from dataclasses import dataclass
from threading import Lock

class Fenced(Exception):
    pass

@dataclass(frozen=True)
class Snapshot:
    generation: int
    version: int
    value: str

class SyntheticFencedStore:
    """Serializes takeover and mutation at one simulated remote boundary."""
    def __init__(self):
        self._lock = Lock()
        self._generation = 0
        self._version = 0
        self._value = "initial"
        self._completed = {}

    def acquire(self):
        with self._lock:
            self._generation += 1
            return self._generation

    def snapshot(self):
        with self._lock:
            return Snapshot(self._generation, self._version, self._value)

    def write(self, generation, expected_version, request_id, value):
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id required")
        with self._lock:
            # Reject stale generations before considering retries.
            if generation != self._generation:
                raise Fenced("stale generation")
            if request_id in self._completed:
                previous = self._completed[request_id]
                if previous[0] != (generation, expected_version, value):
                    raise Fenced("conflicting idempotency request")
                return previous[1]
            if expected_version != self._version:
                raise Fenced("version conflict")
            self._version += 1
            self._value = value
            result = Snapshot(self._generation, self._version, self._value)
            self._completed[request_id] = ((generation, expected_version, value), result)
            return result
