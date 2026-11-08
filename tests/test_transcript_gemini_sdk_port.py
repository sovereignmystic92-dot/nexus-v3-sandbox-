import unittest
from types import SimpleNamespace
from nexus_sandbox.transcript_gemini_sdk_port import make_gemini_sdk_port

class GeminiSdkPortTests(unittest.TestCase):
    def factory(self, response=None, calls=None):
        if calls is None: calls=[]
        if response is None: response=SimpleNamespace(text="Review text",response_id="provider-response-1")
        def build(*,api_key):
            calls.append(("key_received",bool(api_key)))
            return SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw: (calls.append(kw),response)[1]))
        return build,calls
    def test_response_id_preserved(self):
        factory,calls=self.factory()
        port=make_gemini_sdk_port(api_key="synthetic-secret",client_factory=factory)
        self.assertEqual(port("gemini-3.5-flash-lite","Review source"),("Review text","provider-response-1"))
        self.assertEqual(calls[-1]["model"],"gemini-3.5-flash-lite")
    def test_missing_credential_rejected(self):
        with self.assertRaises(ValueError):
            make_gemini_sdk_port(api_key="",client_factory=lambda **kw: None)
    def test_missing_provider_response_id_rejected(self):
        factory,_=self.factory(SimpleNamespace(text="Review",response_id=None))
        with self.assertRaises(ValueError):
            make_gemini_sdk_port(api_key="synthetic",client_factory=factory)("gemini-3.5-flash-lite","Prompt")
    def test_empty_review_rejected(self):
        factory,_=self.factory(SimpleNamespace(text="",response_id="id"))
        with self.assertRaises(ValueError):
            make_gemini_sdk_port(api_key="synthetic",client_factory=factory)("gemini-3.5-flash-lite","Prompt")
    def test_oversized_prompt_rejected_before_api(self):
        factory,calls=self.factory()
        port=make_gemini_sdk_port(api_key="synthetic",client_factory=factory)
        with self.assertRaises(ValueError):
            port("gemini-3.5-flash-lite","x"*100001)
        self.assertEqual(len(calls),1)
    def test_invalid_model_rejected(self):
        factory,calls=self.factory()
        port=make_gemini_sdk_port(api_key="synthetic",client_factory=factory)
        with self.assertRaises(ValueError):
            port("../invalid","Prompt")
        self.assertEqual(len(calls),1)
