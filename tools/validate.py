"""Reproduce local evidence; never equate it with isolated full acceptance."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexus_sandbox.authority import default_records
from nexus_sandbox.contracts import Request
from nexus_sandbox.coordinator import SQLiteCoordinator, digest


class Results(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.cases.append({"test_id": test.id(), "status": "PASSED"})

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.cases.append({"test_id": test.id(), "status": "FAILED"})

    def addError(self, test, error):
        super().addError(test, error)
        self.cases.append({"test_id": test.id(), "status": "ERROR"})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.cases.append({"test_id": test.id(), "status": "SKIPPED"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Explicit local JSON evidence file")
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for folder in ("src", "tests", "tools") for p in sorted((ROOT / folder).rglob("*"))
                if p.is_file() and p.suffix in (".py", ".sql", ".json")}
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests/unit"))
    # Detailed failures stay in the operator's process; report stores statuses only.
    with redirect_stdout(stream), redirect_stderr(stream):
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Results).run(suite)
    distinct = len({c["test_id"] for c in result.cases})
    passed = (result.wasSuccessful() and not result.skipped and result.testsRun > 0
              and distinct == result.testsRun and len(result.cases) == result.testsRun)
    mission_ids = {
        "M01": "test_missions.MissionTests.test_m01_complete_mission_and_repeat_are_durable",
        "M02": "test_missions.MissionTests.test_m02_interrupted_mission_resumes_without_duplicate_work",
        "M03": "test_missions.MissionTests.test_m03_incomplete_evidence_holds_whole_mission",
        "M04": "test_missions.MissionTests.test_m04_current_authority_conflict_holds_whole_mission",
    }
    statuses = {case["test_id"]: case["status"] for case in result.cases}
    mission_cases = [{"case_id": case, "test_id": test,
                      "status": statuses.get(test, "NOT_RUN")}
                     for case, test in mission_ids.items()]
    missions_passed = all(case["status"] == "PASSED" for case in mission_cases)
    passed = passed and missions_passed
    report = {
        "schema_version": 1, "started_at_utc": started,
        "scope": "synthetic local unit/integration evidence only",
        "local_test_status": "PASSED" if passed else "FAILED",
        "tests_run": result.testsRun, "distinct_tests": distinct, "cases": result.cases,
        "mission_cases": mission_cases,
        "mission_status": "PASSED" if missions_passed else "FAILED",
        "mission_scope": "single transaction per mission; payload preservation only; no semantic synthesis or external registration",
        "source_sha256": manifest,
        "full_acceptance_status": "BLOCKED",
        "unresolved_controls": ["C1 disposable host/filesystem isolation", "C2 effective grants",
                                "C3 production credential/mount exclusion", "C4 host egress/trigger denial",
                                "C8 host stop/teardown and retention verification"],
        "deferred_scope": ["F04 reciprocal external endpoints", "F05 disk-full/power-loss",
                           "C01 concurrent workers", "C02/C9 worker lease fencing"],
        "limitations": ["no automatic isolation probe or external integration in this runner",
                        "runtime/authority labels are operator assertions; no independent human audit",
                        "test failures do not prove a database write succeeded"],
        "sample_attempts": [],
    }
    if passed:
        fixture = json.loads((ROOT / "tests/fixtures/complete-source.json").read_text())
        with tempfile.TemporaryDirectory(prefix="nexus-evidence-") as temporary:
            path = Path(temporary) / "evidence.sqlite"
            coordinator = SQLiteCoordinator(path, [fixture], case_id="S01",
                                            runtime_identity="synthetic:runtime:validation-runner")
            request = Request(fixture["idempotency_key"], fixture["source_id"], fixture["source_revision"],
                              fixture["destination_id"], digest(fixture["payload"]), True)
            cp = coordinator.submit(request)
            for _ in range(5):
                cp = coordinator.resume(cp.transaction_id, cp.version)
            if cp.state != "VERIFIED":
                raise RuntimeError("Synthetic evidence example did not verify")
            authority = default_records() + [dict(default_records()[0],
                document_id="synthetic:authority:conflict", rule="deny_synthetic_output")]
            blocked = SQLiteCoordinator(path, [fixture], authority_records=authority,
                case_id="AUTH-CONFLICT", runtime_identity="synthetic:runtime:validation-runner")
            held = blocked.submit(replace(request, idempotency_key="synthetic:request:conflict"))
            if held.disposition != "BLOCKED":
                raise RuntimeError("Synthetic authority conflict did not block")
            with sqlite3.connect(path) as db:
                report["sample_attempts"] = [json.loads(r[0]) for r in db.execute(
                    "SELECT envelope_json FROM attempts ORDER BY rowid")]
    report["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(output)
        print(json.dumps({"local_test_status": report["local_test_status"],
                          "distinct_tests": distinct, "full_acceptance_status": "BLOCKED"}))
    else:
        print(output, end="")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
