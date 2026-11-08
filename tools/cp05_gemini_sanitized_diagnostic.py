"""CP05 shell diagnostic: public-contract and runner metadata only.

Never reads Socra secrets or invokes Socra OAuth. Gemini receives a fixed,
non-sensitive diagnostic envelope, never raw subprocess logs.
"""
import json
import os
import sys
from pathlib import Path
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
    if os.environ.get("CP05_GEMINI_COST_APPROVED") != "true":
        print("GEMINI_REVIEW=BLOCKED_COST_APPROVAL")
        return
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from nexus_sandbox.csf_gemini_model_selection import select_gemini_model, GeminiModelSelectionError
    try:
        model = select_gemini_model(key)
        payload = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": PROMPT + "\\n" + json.dumps(report, sort_keys=True)}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 512}
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent",
            data=payload, method="POST",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=25) as response:
            if response.status != 200:
                raise ValueError("provider_status")
            raw = response.read(8193)
        if len(raw) > 8192:
            raise ValueError("response_too_large")
        result = json.loads(raw)
        candidates = result.get("candidates", [])
        if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
            raise ValueError("response_not_finished")
        text = candidates[0]["content"]["parts"][0]["text"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("empty_review")
        # Review content remains ephemeral; only receipt metadata enters logs.
        print("GEMINI_REVIEW=COMPLETED_CONTEXT_ONLY")
        print("GEMINI_REVIEW_RECEIPT=" + json.dumps({
            "provider_called": True, "review_received": True,
            "external_writes": 0, "socra_authenticated": False,
            "audit_gate_promoted": False}, sort_keys=True))
    except (GeminiModelSelectionError, urllib.error.HTTPError,
            urllib.error.URLError, TimeoutError, ValueError, KeyError,
            IndexError, TypeError, OSError):
        print("GEMINI_REVIEW=BLOCKED_PROVIDER_OR_RESPONSE")
        sys.exit(2)

if __name__ == "__main__":
    main()
