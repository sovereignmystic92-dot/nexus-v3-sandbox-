"""Explicit C06 live synthetic update probe via host JSON-line callback.

Run once with --journal PATH. Retain the journal; do not remove it to retry an
uncertain write. This probe only updates the named C05 registry from v1 to v2.
No credentials, direct network client, create or delete operation is provided.
"""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nexus_sandbox.cortex_adapter import CortexAdapter, Write
from nexus_sandbox.cortex_tools import CortexToolTransport

SOURCE = "Nexus Sandbox C01 — Synthetic Source — 2026-10-22"
TARGET = "Nexus Sandbox C05 — Synthetic Registry — 2026-10-22"
DEPENDENCY = "Nexus Sandbox C05 — Synthetic Output — 2026-10-22"
NAMES = frozenset((SOURCE, TARGET, DEPENDENCY))
KEY = "synthetic:request:cortex-C06-update"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    if sys.stdin.isatty():
        import termios
        settings = termios.tcgetattr(sys.stdin)
        settings[3] &= ~termios.ECHO
        termios.tcsetattr(sys.stdin, termios.TCSANOW, settings)
    calls = []

    def invoke(tool, arguments):
        if (tool not in ("context_get", "context_update") or arguments["name"] not in NAMES
                or tool == "context_update" and arguments["name"] != TARGET):
            raise ValueError("Probe scope violation")
        print(json.dumps({"rpc": tool, "arguments": arguments}), flush=True)
        line = sys.stdin.readline()
        if not line:
            raise RuntimeError("Host disconnected; reconcile saved journal")
        result = json.loads(line)
        calls.append({"tool": tool, "name": arguments["name"], "isError": bool(result.get("isError"))})
        return result

    transport = CortexToolTransport(invoke)
    source = transport.get(SOURCE)
    before = transport.get(TARGET)
    if source is None or source.version != 2 or before is None or before.version != 1:
        raise RuntimeError("Expected source v2 and exact target v1; no update")
    content = before.content + "\nC06 bounded update marker: " + KEY + "\nSynthetic only; no canonical promotion."
    request = Write(KEY, TARGET, content, before.dependencies, source, before)
    outcomes = []

    def ensure(plan, label):
        result = CortexAdapter(args.journal, NAMES, transport).ensure(plan)
        outcomes.append({"label": label, **asdict(result)})
        return result

    first = ensure(request, "live_update")
    if first.operation_outcome != "SUCCEEDED" or first.protocol_verdict != "VERIFIED":
        raise RuntimeError("Update unverified; preserve journal and reconcile")
    repeat = ensure(request, "exact_repeat")
    if repeat.operation_outcome != "NOT_ATTEMPTED" or repeat.protocol_verdict != "VERIFIED":
        raise RuntimeError("Repeat unverified")
    stale_key = "synthetic:request:cortex-C06-stale"
    stale = replace(request, key=stale_key, content=before.content + "\n" + stale_key)
    conflict = ensure(stale, "stale_target_guard")
    if (conflict.operation_outcome, conflict.protocol_verdict, conflict.checkpoint) != (
            "NOT_ATTEMPTED", "BLOCKED", "TARGET_CONFLICT"):
        raise RuntimeError("Stale target guard failed")
    after = transport.get(TARGET)
    if (after is None or after.id != before.id or after.version != 2
            or after.content != content or after.dependencies != before.dependencies):
        raise RuntimeError("Post-conflict saved state changed unexpectedly")
    print(json.dumps({"probe_result": "PASSED", "request": asdict(request),
                      "after": asdict(after), "outcomes": outcomes, "calls": calls,
                      "limitation": "Client preflight and readback only; no atomic CAS or concurrent-writer protection."}), flush=True)


if __name__ == "__main__":
    main()
