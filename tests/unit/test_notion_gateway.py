"""Fake HTTPS boundary only. No real credential or socket is used."""

from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from nexus_sandbox.notion_adapter import Binding, NotionAdapter
from nexus_sandbox.notion_gateway import GatewayError, NotionGateway
from nexus_sandbox.notion_rest import API_VERSION, NotionRESTTransport, create_body
from test_notion_rest import ROOT, PAGE, OTHER, Service

TOKEN = "synthetic_gateway_token_never_a_real_secret"
HEADERS = {"Notion-Version": API_VERSION}


class Response:
    def __init__(self, data, status=200):
        self.status = status
        self.stream = io.BytesIO(json.dumps(data).encode())

    def read1(self, size):
        return self.stream.read(size)


class FakeHTTPS:
    def __init__(self, service):
        self.service = service
        self.connections = []
        self.requests = []
        self.closes = 0
        self.status = 200
        self.raw = None
        self.fail = False

    def __call__(self, host, **kwargs):
        self.connections.append((host, kwargs))
        return self

    def request(self, method, target, *, body, headers):
        self.requests.append((method, target, body, headers))
        if self.fail:
            raise RuntimeError("synthetic error containing " + TOKEN)

    def getresponse(self):
        method, target, body, headers = self.requests[-1]
        if self.raw is not None:
            response = Response({})
            response.stream = io.BytesIO(self.raw)
            return response
        if self.status != 200:
            return Response({"body_must_not_be_exposed": TOKEN}, self.status)
        url = urlsplit(target)
        query = {k: v[0] for k, v in parse_qs(url.query).items()} or None
        if query:
            query["page_size"] = int(query["page_size"])
        result = self.service(method, url.path.removeprefix("/v1"), query=query,
                              body=json.loads(body) if body else None,
                              headers={"Notion-Version": headers["Notion-Version"]})
        return Response(result)

    def close(self):
        self.closes += 1


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.service = Service()
        self.http = FakeHTTPS(self.service)
        self.token_calls = 0
        def token():
            self.token_calls += 1
            return TOKEN
        self.gateway = NotionGateway(ROOT, token, enabled=True, connection_factory=self.http)
        self.binding = Binding("synthetic:request:gateway", ROOT, self.service.title, "Fictional gateway payload")

    def getroot(self):
        return self.gateway("GET", "/pages/" + ROOT, headers=HEADERS)

    def test_disabled_default_never_calls_provider_or_opens_connection(self):
        gateway = NotionGateway(ROOT, lambda: self.fail("Secret provider must stay unused"), connection_factory=self.http)
        with self.assertRaises(GatewayError):
            gateway("GET", "/pages/" + ROOT, headers=HEADERS)
        self.assertEqual(self.http.connections, [])

    def test_fixed_https_origin_tls_version_and_close(self):
        self.getroot()
        host, options = self.http.connections[0]
        self.assertEqual((host, options["port"], options["timeout"]), ("api.notion.com", 443, 10))
        self.assertTrue(options["context"].check_hostname)
        self.assertEqual(self.http.requests[0][1], "/v1/pages/" + ROOT)
        self.assertEqual(self.http.closes, 1)
        self.assertNotIn(TOKEN, repr(self.gateway))

    def test_absolute_url_extra_headers_and_mutating_methods_are_rejected(self):
        cases = [("GET", "https://evil.invalid/", HEADERS),
                 ("DELETE", "/pages/" + ROOT, HEADERS),
                 ("GET", "/pages/" + ROOT, dict(HEADERS, Authorization="untrusted")),
                 ("PATCH", "/pages/" + ROOT, HEADERS)]
        for method, path, headers in cases:
            with self.subTest(path=path, method=method), self.assertRaises(GatewayError):
                self.gateway(method, path, headers=headers)
        self.assertEqual(self.token_calls, 0)

    def test_undiscovered_child_is_rejected_before_authentication(self):
        with self.assertRaises(GatewayError):
            self.gateway("GET", "/pages/" + PAGE, headers=HEADERS)
        self.assertEqual(self.token_calls, 0)

    def test_new_child_requires_validated_parent_before_body_access(self):
        self.gateway._children.add(PAGE.replace("-", ""))
        with self.assertRaises(GatewayError):
            self.gateway("GET", "/blocks/" + PAGE + "/children", query={"page_size": 100}, headers=HEADERS)
        self.service.parent = OTHER
        with self.assertRaises(GatewayError):
            self.gateway("GET", "/pages/" + PAGE, headers=HEADERS)
        self.assertEqual(len(self.http.requests), 1)

    def test_full_fake_https_create_readback_and_repeat(self):
        with tempfile.TemporaryDirectory(prefix="notion-gateway-offline-") as temporary:
            transport = NotionRESTTransport(ROOT, self.gateway)
            engine = NotionAdapter(Path(temporary) / "journal.sqlite", ROOT, transport)
            self.assertEqual(engine.ensure(self.binding).status, "VERIFIED")
            self.assertEqual(engine.ensure(self.binding).status, "VERIFIED")
        self.assertEqual(sum(r[0] == "POST" for r in self.http.requests), 1)
        self.assertEqual(self.http.closes, len(self.http.connections))

    def test_lost_create_reply_through_gateway_reconciles_without_retry(self):
        self.service.lose_post = True
        with tempfile.TemporaryDirectory(prefix="notion-gateway-loss-") as temporary:
            journal = Path(temporary) / "receipts.sqlite"
            def engine():
                return NotionAdapter(journal, ROOT, NotionRESTTransport(ROOT, self.gateway))
            self.assertEqual(engine().ensure(self.binding).status, "UNKNOWN")
            self.assertEqual(engine().ensure(self.binding).status, "VERIFIED")
        self.assertEqual(sum(r[0] == "POST" for r in self.http.requests), 1)

    def test_modified_create_body_or_target_rejected_without_secret(self):
        original = create_body(self.binding)
        cases = []
        for field, value in (("parent", {"page_id": OTHER}), ("icon", {"type": "emoji", "emoji": "X"})):
            body = deepcopy(original)
            body[field] = value
            cases.append(body)
        body = deepcopy(original)
        body["children"][0]["code"]["rich_text"][0]["text"]["content"] = "{}"
        cases.append(body)
        for body in cases:
            with self.subTest(body=body), self.assertRaises(GatewayError):
                self.gateway("POST", "/pages", body=body, headers=HEADERS)
        self.assertEqual(self.token_calls, 0)

    def test_redirect_rate_limit_and_server_error_are_not_followed_or_retried(self):
        for status in (302, 429, 500):
            self.http.status = status
            before = len(self.http.requests)
            with self.subTest(status=status), self.assertRaises(GatewayError) as raised:
                self.getroot()
            self.assertEqual(len(self.http.requests), before + 1)
            self.assertNotIn(TOKEN, str(raised.exception))

    def test_oversized_response_and_non_json_are_rejected(self):
        for raw in (b"x" * 1048577, b"not-json-" + TOKEN.encode()):
            self.http.raw = raw
            with self.subTest(size=len(raw)), self.assertRaises(GatewayError) as raised:
                self.getroot()
            self.assertNotIn(TOKEN, str(raised.exception))

    def test_exception_with_secret_is_redacted_and_connection_closed(self):
        self.http.fail = True
        with self.assertRaises(GatewayError) as raised:
            self.getroot()
        self.assertNotIn(TOKEN, str(raised.exception))
        self.assertEqual(self.http.closes, 1)

    def test_time_and_request_budgets_stop_before_credential_lookup(self):
        self.gateway._requests = 200
        with self.assertRaises(GatewayError):
            self.getroot()
        self.gateway._requests = 0
        self.gateway._deadline = 0
        with self.assertRaises(GatewayError):
            self.getroot()
        self.assertEqual(self.token_calls, 0)

    def test_failed_metadata_refresh_invalidates_previous_body_grant(self):
        self.gateway._children.add(PAGE.replace("-", ""))
        self.gateway("GET", "/pages/" + PAGE, headers=HEADERS)
        self.http.status = 403
        with self.assertRaises(GatewayError):
            self.gateway("GET", "/pages/" + PAGE, headers=HEADERS)
        with self.assertRaises(GatewayError):
            self.gateway("GET", "/blocks/" + PAGE + "/children", query={"page_size": 100}, headers=HEADERS)
