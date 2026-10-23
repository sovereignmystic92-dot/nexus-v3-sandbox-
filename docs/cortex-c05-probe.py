"""Explicit C05 synthetic live probe; host services JSON-line tool requests.

Run with --journal PATH. No credentials, automatic network client or scheduler.
The host must allow only the three printed Cortex operation names and fixture
names. Standard input carries original authenticated tool-result dictionaries.
"""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nexus_sandbox.cortex_adapter import CortexAdapter, MARKER, Write
from nexus_sandbox.cortex_tools import CortexToolTransport

SOURCE = "Nexus Sandbox C01 — Synthetic Source — 2026-10-22"
ARCHIVE = "Nexus Sandbox C05 — Synthetic Archive — 2026-10-22"
OUTPUT = "Nexus Sandbox C05 — Synthetic Output — 2026-10-22"
REGISTRY = "Nexus Sandbox C05 — Synthetic Registry — 2026-10-22"
NAMES = frozenset((SOURCE, ARCHIVE, OUTPUT, REGISTRY))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()
    # Disable terminal echo when an interactive host is used; responses contain
    # account metadata and must not be echoed into the public evidence report.
    if sys.stdin.isatty():
        import termios
        settings = termios.tcgetattr(sys.stdin)
        settings[3] &= ~termios.ECHO
        termios.tcsetattr(sys.stdin, termios.TCSANOW, settings)
    calls = []
    drop_output_ack = True

    def invoke(tool, arguments):
        nonlocal drop_output_ack
        if (tool not in ("context_get", "context_create", "context_update")
                or arguments["name"] not in NAMES
                or tool != "context_get" and arguments["name"] == SOURCE):
            raise ValueError("Probe scope violation")
        print(json.dumps({"rpc": tool, "arguments": arguments}), flush=True)
        line = sys.stdin.readline()
        if not line:
            raise RuntimeError("Host disconnected; reconcile journal before rerun")
        result = json.loads(line)
        calls.append({"tool": tool, "name": arguments["name"], "isError": bool(result.get("isError"))})
        if tool == "context_create" and arguments["name"] == OUTPUT and not result.get("isError") and drop_output_ack:
            drop_output_ack = False
            # Actual tool response has arrived. Discard it at the callback
            # boundary to exercise uncertainty; this is NOT a network outage.
            raise TimeoutError("Deliberate local acknowledgment discard")
        return result

    transport = CortexToolTransport(invoke)
    source = transport.get(SOURCE)
    if source is None or source.version != 2:
        raise RuntimeError("Pinned source v2 unavailable; no writes authorized")
    outcomes = []

    def ensure(request, label):
        result = CortexAdapter(args.journal, NAMES, transport).ensure(request)
        outcomes.append({"label": label, **asdict(result)})
        return result

    stale_key = "synthetic:request:cortex-C05-stale"
    stale = Write(stale_key, ARCHIVE, MARKER + "\n" + stale_key,
                  (SOURCE,), replace(source, version=1))
    if ensure(stale, "stale_source_guard").checkpoint != "SOURCE_CHANGED":
        raise RuntimeError("Stale source guard failed")

    previous = SOURCE
    bindings = []
    for index, name in enumerate((ARCHIVE, OUTPUT, REGISTRY)):
        key = "synthetic:request:cortex-C05-stage-" + str(index)
        content = MARKER + "\n" + key + "\nC05 live adapter fixture; no canonical authority.\n" + json.dumps({
            "source": asdict(source), "stage": index, "previous_name": previous,
            "purpose": "Persistence and exact reuse only; Notion integration remains paused."
        }, sort_keys=True, ensure_ascii=False)
        request = Write(key, name, content, (previous,), source)
        first = ensure(request, "stage_" + str(index) + "_first")
        second = ensure(request, "stage_" + str(index) + "_repeat")
        if second.protocol_verdict != "VERIFIED" or second.operation_outcome != "NOT_ATTEMPTED":
            raise RuntimeError("Repeat/reconciliation failed")
        if first.protocol_verdict not in ("VERIFIED", "UNKNOWN"):
            raise RuntimeError("Initial stage failed")
        bindings.append({"request": asdict(request), "module_id": second.module_id,
                         "module_version": second.module_version})
        previous = name
    print(json.dumps({"probe_result": "PASSED", "outcomes": outcomes,
                      "bindings": bindings, "calls": calls,
                      "limitation": "Output acknowledgment deliberately discarded locally after successful tool reply; no actual network outage."}), flush=True)


if __name__ == "__main__":
    main()
