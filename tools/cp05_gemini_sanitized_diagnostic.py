"""CP05 shell diagnostic: public-contract and runner metadata only.

Never reads Socra secrets or invokes Socra OAuth. Gemini receives a fixed,
non-sensitive diagnostic envelope, never raw subprocess logs.
"""
import json
import os
import sys
import urllib.error
import urllib.request

PROMPT = """Review this sanitized CP05 Socra OAuth integration diagnostic.
Known verified facts: GitHub Actions previously passed a secret-presence
check; this does not prove validity. Official Socra CLI reference states
installation listing requires an authenticated Account context and token
creation requires client, principal and client-secret-file. The GitHub
runner principal is not verified. No provider request or Cortex write was
attempted. Identify only actionable gaps and safe next steps; do not claim
successful authentication. Do not propose guessed endpoints or bypasses.
Return concise text, maximum 800 words."""

def envelope():
    return {
        "issue": 260,
        "contract_url": "https://cloud.socra.com/docs/oauth/reference/cli",
        "credential_presence_prior_run": "42475264163:success",
        "account_context_available": "not_verified",
        "runner_principal_verified": False,
        "provider_authenticated": False,
        "provider_called": False,
        "external_writes": 0,
        "audit_gate_promoted": False,
    }

def main():
    # Fixed allowlisted envelope only. Never transmit environment or secrets.
    report = envelope()
    print("CP05_DIAGNOSTIC=" + json.dumps(report, sort_keys=True))
    if os.environ.get("CP05_GEMINI_REVIEW_APPROVED") != "true":
        print("GEMINI_REVIEW=SKIPPED_NOT_APPROVED")
        return
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("Gemini key unavailable")
    # Do not call a model without a verified model/endpoint contract.
    # Existing approved Gemini pilot uses its own pinned, bounded adapter.
    print("GEMINI_REVIEW=BLOCKED_ADAPTER_NOT_WIRED")

if __name__ == "__main__":
    main()
