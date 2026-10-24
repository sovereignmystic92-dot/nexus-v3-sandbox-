"""One synthetic Gemini request. No app writes, retries, or arbitrary prompts."""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

MODEL = "gemini-3.5-flash-lite"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
PROMPT = (
    "Analyze this fictional scheduling task using only the two sources. "
    "S1: Willow Library opens Tuesday-Saturday 09:00-17:00 and closes Sunday-Monday. "
    "S2: Mira requests a two-hour workshop Monday at 10:00, alternatively Tuesday at 10:00. "
    "Room availability and facilitator availability are unknown. "
    "Explain which proposal fits opening hours, cite S1/S2, and identify what remains "
    "unconfirmed. Do not claim a booking, external verification, or tool use."
)
MAX_RESPONSE_BYTES = 65536


class BridgeError(Exception):
    """Safe fixed diagnostic; never expose provider bodies or request headers."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BridgeError("REDIRECT_REFUSED")


def run(environ, opener=None):
    if environ.get("GEMINI_FREE_TIER_CONFIRMED") != "true":
        raise BridgeError("FREE_TIER_CONFIRMATION_REQUIRED")
    key = environ.get("GEMINI_API_KEY", "").strip()
    if not key or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise BridgeError("KEY_MISSING_OR_INVALID")
    payload = {
        "contents": [{"role": "user", "parts": [{"text": PROMPT}]}],
        "generationConfig": {"maxOutputTokens": 512, "temperature": 0},
    }
    request = urllib.request.Request(
        URL, data=json.dumps(payload).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
    )
    # Disable proxy inheritance and cross-origin redirects carrying the key.
    opener = opener or urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect()
    )
    try:
        with opener.open(request, timeout=45) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise BridgeError(f"HTTP_{exc.code}_NO_RETRY") from None
    except (OSError, ValueError):
        raise BridgeError("TRANSPORT_UNCERTAIN_NO_RETRY") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise BridgeError("RESPONSE_TOO_LARGE")
    try:
        data = json.loads(raw)
        candidate = data["candidates"][0]
        if candidate.get("finishReason") != "STOP":
            raise BridgeError("INCOMPLETE_OR_BLOCKED_RESPONSE")
        parts = candidate["content"]["parts"]
        if not isinstance(parts, list) or not parts:
            raise BridgeError("NON_TEXT_RESPONSE")
        texts = []
        for part in parts:
            # REST text parts may carry opaque signatures and a thought flag.
            # This single-turn pilot never replays signatures or emits thoughts.
            if (not isinstance(part, dict)
                    or set(part) - {"text", "thought", "thoughtSignature"}
                    or not isinstance(part.get("text"), str)
                    or ("thought" in part and type(part["thought"]) is not bool)
                    or ("thoughtSignature" in part and not isinstance(part["thoughtSignature"], str))):
                raise BridgeError("NON_TEXT_RESPONSE")
            if not part.get("thought", False):
                texts.append(part["text"])
        answer = "\n".join(texts).strip()
        if not answer or key in answer:
            raise BridgeError("EMPTY_OR_SENSITIVE_RESPONSE")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise BridgeError("INVALID_PROVIDER_RESPONSE") from None
    return {
        "task_id": "synthetic:nexus-handoff:library-001",
        "requested_model": MODEL,
        "source_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(),
        "operation": "ANALYSIS_RECEIVED", "knowledge": "PROPOSED",
        "app_writes": "NOT_ATTEMPTED", "answer": answer,
    }


if __name__ == "__main__":
    try:
        # One escaped line prevents model text from becoming workflow commands.
        print("NEXUS_GEMINI_RESULT " + json.dumps(run(os.environ), ensure_ascii=True))
    except BridgeError as exc:
        print("NEXUS_GEMINI_STATUS " + str(exc))
        sys.exit(1)
    except Exception:
        print("NEXUS_GEMINI_STATUS UNEXPECTED_FAILURE_DETAILS_SUPPRESSED")
        sys.exit(1)
