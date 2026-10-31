"""CP01/CP03 workflow source checks; never claims host-side secret absence.

Checks tracked no-credential jobs for accidental GitHub secret/context references.
This is code review evidence, not an inventory of the GitHub runner host,
environment secret values, GitHub Apps, connectors, or provider grants.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
NO_CREDENTIAL_WORKFLOWS = (
    "synthetic-acceptance.yml",
    "gemini-offline.yml",
    "cp04-environment-enforcement-probe.yml",
    "cp04-host-reachability-observation.yml",
)
SECRET_EXPRESSION = re.compile(r"\$\{\{\s*(?:secrets\.|github\.token\b)", re.I)
ENV_SECRET_NAME = re.compile(r"\b(?:GITHUB_TOKEN|GH_TOKEN|NOTION_SANDBOX_TOKEN|GEMINI_API_KEY)\s*:", re.I)


def assess_workflow(text):
    return {
        "explicit_no_write_permissions": bool(re.search(r"(?m)^permissions:\s*\{\}\s*$", text)),
        "no_secret_context": not bool(SECRET_EXPRESSION.search(text)),
        "no_known_token_env_assignment": not bool(ENV_SECRET_NAME.search(text)),
    }


def inspect(root=ROOT):
    results = {}
    for name in NO_CREDENTIAL_WORKFLOWS:
        path = root / ".github" / "workflows" / name
        results[name] = assess_workflow(path.read_text())
    passed = all(all(result.values()) for result in results.values())
    return {
        "schema_version": 1,
        "scope": "REVIEWED_NO_CREDENTIAL_WORKFLOW_SOURCE_ONLY",
        "source_checks_passed": passed,
        "checks": results,
        "host_secret_exclusion_proven": False,
        "host_trust_independently_assessed": False,
        "cp01_verdict": "PARTIALLY_VERIFIED",
        "cp03_verdict": "PARTIALLY_VERIFIED",
        "limitations": [
            "Text checks do not prove host runtime secret/mount exclusion",
            "No provider-side or GitHub environment secret values are read",
            "No GitHub App, ChatGPT connector, or automation host inventory is established",
        ],
    }


if __name__ == "__main__":
    report = inspect()
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(0 if report["source_checks_passed"] else 2)
