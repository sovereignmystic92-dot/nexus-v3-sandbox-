"""C11 synthetic uncertain-update/restart probe via host JSON-line callback.

Use --mode write once, then --mode reconcile in a separate Python process with
the same --journal and --plan. Never reset either file to retry uncertainty.
No credentials, direct network client, create or delete operation is provided.
"""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nexus_sandbox.cortex_adapter import CortexAdapter, Module, Write
from nexus_sandbox.cortex_tools import CortexToolTransport

SOURCE = "Nexus Sandbox C01 — Synthetic Source — 2026-10-22"
TARGET = "Nexus Sandbox C05 — Synthetic Registry — 2026-10-22"
DEPENDENCY = "Nexus Sandbox C05 — Synthetic Output — 2026-10-22"
NAMES = frozenset((SOURCE, TARGET, DEPENDENCY))
KEY = "synthetic:request:cortex-C11-update"


def decode_module(data):
    return Module(data["id"], data["name"], data["version"], data["content"], tuple(data["dependencies"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("write", "reconcile"), required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    if sys.stdin.isatty():
        import termios
        settings = termios.tcgetattr(sys.stdin)
        settings[3] &= ~termios.ECHO
        termios.tcsetattr(sys.stdin, termios.TCSANOW, settings)
    calls = []
    discarded = False

    def invoke(tool, arguments):
        nonlocal discarded
        if (tool not in ("context_get", "context_update") or arguments["name"] not in NAMES
                or tool == "context_update" and (arguments["name"] != TARGET or args.mode != "write")):
            raise ValueError("Probe scope violation")
        print(json.dumps({"rpc": tool, "arguments": arguments}), flush=True)
        line = sys.stdin.readline()
        if not line:
            raise RuntimeError("Host disconnected; retain journal and plan")
        result = json.loads(line)
        calls.append({"tool": tool, "name": arguments["name"], "isError": bool(result.get("isError"))})
        if tool == "context_update" and not result.get("isError") and not discarded:
            discarded = True
            # Real service reply received; deliberately discard locally. This
            # exercises uncertain acknowledgment, not an actual network outage.
            raise TimeoutError("Deliberate local update acknowledgment discard")
        return result

    transport = CortexToolTransport(invoke)
    if args.mode == "write":
        if args.plan.exists() or args.journal.exists():
            raise RuntimeError("Existing plan/journal: reconcile rather than write")
        source, before = transport.get(SOURCE), transport.get(TARGET)
        if source is None or source.version != 2 or before is None or before.version != 2:
            raise RuntimeError("Expected source v2 and registry v2; no update")
        content = before.content + "\nC11 bounded uncertain-update marker: " + KEY + "\nSynthetic only; retain for review."
        request = Write(KEY, TARGET, content, before.dependencies, source, before)
        # Exclusive plan creation precedes durable adapter intent and remote write.
        with args.plan.open("x") as output:
            json.dump(asdict(request), output)
        result = CortexAdapter(args.journal, NAMES, transport).ensure(request)
        if (result.operation_outcome, result.protocol_verdict, result.checkpoint) != (
                "UNKNOWN", "UNKNOWN", "RECONCILE_ONLY") or not discarded:
            raise RuntimeError("Expected uncertain update; retain state for investigation")
        print(json.dumps({"probe_result": "UNCERTAIN_CHECKPOINT_SAVED", "mode": args.mode,
                          "request": asdict(request), "outcomes": [{"label": "discarded_update_reply", **asdict(result)}],
                          "calls": calls}), flush=True)
        return

    if not args.plan.exists() or not args.journal.exists():
        raise RuntimeError("Original plan and journal required")
    data = json.loads(args.plan.read_text())
    request = Write(data["key"], data["name"], data["content"], tuple(data["dependencies"]),
                    decode_module(data["source"]), decode_module(data["before"]))
    outcomes = []
    for label in ("after_process_restart", "exact_repeat"):
        result = CortexAdapter(args.journal, NAMES, transport).ensure(request)
        outcomes.append({"label": label, **asdict(result)})
        if result.operation_outcome != "NOT_ATTEMPTED" or result.protocol_verdict != "VERIFIED":
            raise RuntimeError("Read-only reconciliation failed")
    stale_key = "synthetic:request:cortex-C11-stale"
    stale = replace(request, key=stale_key, content=request.before.content + "\n" + stale_key)
    result = CortexAdapter(args.journal, NAMES, transport).ensure(stale)
    outcomes.append({"label": "stale_v2_baseline", **asdict(result)})
    if (result.operation_outcome, result.protocol_verdict, result.checkpoint) != (
            "NOT_ATTEMPTED", "BLOCKED", "TARGET_CONFLICT"):
        raise RuntimeError("Stale v2 baseline was not held")
    after = transport.get(TARGET)
    if (after is None or after.id != request.before.id or after.version != 3
            or after.content != request.content or after.dependencies != request.dependencies):
        raise RuntimeError("Exact v3 readback failed")
    print(json.dumps({"probe_result": "PASSED", "mode": args.mode, "request": asdict(request),
                      "after": asdict(after), "outcomes": outcomes, "calls": calls,
                      "limitation": "Local acknowledgment discard; no real network outage, power loss or concurrent writer."}), flush=True)


if __name__ == "__main__":
    main()
