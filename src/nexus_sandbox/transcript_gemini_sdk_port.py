"""Credential-scoped Gemini SDK port for source-bound Nexus review.

Caller must explicitly provide the API key at the host boundary. No writes,
logging of prompt/credentials, or implicit fallback to an unauthenticated port.
"""
import re

_MODEL = re.compile(r"gemini-[a-zA-Z0-9._-]{1,70}\Z")


def make_gemini_sdk_port(*, api_key, client_factory=None):
    """Return a (model, prompt) -> (text, provider_response_id) port.

    The provider response ID is an audit correlation token, not proof of
    identity by itself. Host must independently authenticate the API call.
    """
    if type(api_key) is not str or not api_key.strip():
        raise ValueError("Gemini API credential required")
    if client_factory is None:
        from google import genai
        client_factory = genai.Client
    if not callable(client_factory):
        raise ValueError("invalid Gemini SDK factory")
    client = client_factory(api_key=api_key)

    def invoke(model, prompt):
        if type(model) is not str or not _MODEL.fullmatch(model):
            raise ValueError("invalid Gemini model")
        if type(prompt) is not str or not prompt.strip() or len(prompt.encode("utf-8")) > 100000:
            raise ValueError("invalid or oversized Gemini prompt")
        response = client.models.generate_content(model=model, contents=prompt)
        content = getattr(response, "text", None)
        response_id = getattr(response, "response_id", None)
        if type(content) is not str or not content.strip():
            raise ValueError("Gemini returned no review text")
        if type(response_id) is not str or not response_id.strip():
            raise ValueError("Gemini returned no provider response ID")
        return content, response_id
    return invoke
