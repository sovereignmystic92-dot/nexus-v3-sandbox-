"""Bounded Gemini model discovery for approved generateContent models.

Only model identifiers and supported actions are inspected. Never log API data.
"""
import json
import urllib.error
import urllib.request

from .csf_v02 import CSFValidationError

MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=100"
APPROVED_MODELS = ("gemini-3.5-flash-lite",)
MAX_MODEL_LIST_BYTES = 131072


class GeminiModelSelectionError(CSFValidationError):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def select_gemini_model(api_key, *, opener=None):
    request = urllib.request.Request(
        MODELS_URL, headers={"x-goog-api-key": api_key, "Accept": "application/json"})
    transport = opener if opener is not None else urllib.request.urlopen
    try:
        with transport(request, timeout=15) as response:
            if response.status != 200:
                raise GeminiModelSelectionError("MODEL_DISCOVERY_STATUS")
            raw = response.read(MAX_MODEL_LIST_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise GeminiModelSelectionError(
            "MODEL_DISCOVERY_AUTH" if exc.code in (401, 403) else
            "MODEL_DISCOVERY_QUOTA" if exc.code == 429 else
            "MODEL_DISCOVERY_UNAVAILABLE") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise GeminiModelSelectionError("MODEL_DISCOVERY_TRANSPORT") from None
    if len(raw) > MAX_MODEL_LIST_BYTES:
        raise GeminiModelSelectionError("MODEL_DISCOVERY_TOO_LARGE")
    try:
        envelope = json.loads(raw)
        models = envelope["models"]
        if not isinstance(models, list) or envelope.get("nextPageToken"):
            raise ValueError("unbounded model list")
        supported = {
            item["name"].removeprefix("models/")
            for item in models
            if isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and isinstance(item.get("supportedGenerationMethods"), list)
            and "generateContent" in item["supportedGenerationMethods"]
        }
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise GeminiModelSelectionError("MODEL_DISCOVERY_INVALID") from None
    for model in APPROVED_MODELS:
        if model in supported:
            return model
    raise GeminiModelSelectionError("APPROVED_MODEL_UNAVAILABLE")
