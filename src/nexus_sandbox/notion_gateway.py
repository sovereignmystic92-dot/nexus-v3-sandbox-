"""Opt-in fixed-origin HTTPS gateway. No environment reads or stored tokens."""

import http.client
import json
import re
import ssl
import time
from urllib.parse import urlencode

from .notion_adapter import Binding
from .notion_rest import API_VERSION, create_body, text, uuid_key


class GatewayError(RuntimeError):
    pass


class NotionGateway:
    """One bounded session; token_provider supplies a secret only when enabled.

    Authorization remains application-level. The owner must separately restrict
    the actual Notion connection to the test root before any live use.
    connection_factory is a test seam; never pass untrusted implementations.
    """

    def __init__(self, sandbox_parent, token_provider, *, enabled=False,
                 connection_factory=None):
        self.root = uuid_key(sandbox_parent)
        self._token_provider = token_provider
        self.enabled = enabled
        self._factory = connection_factory or http.client.HTTPSConnection
        self._children = set()
        self._validated = set()
        self._requests = 0
        self._deadline = time.monotonic() + 120

    def __repr__(self):
        return "<NotionGateway enabled=" + str(self.enabled is True) + ">"

    def _authorize(self, method, path, query, body, headers):
        if headers != {"Notion-Version": API_VERSION}:
            raise GatewayError("Only the pinned version header is accepted")
        if method == "POST" and path == "/pages" and query is None:
            try:
                if uuid_key(body["parent"]["page_id"]) != self.root:
                    raise ValueError()
                encoded = text(body["children"][0]["code"]["rich_text"])
                record = json.loads(encoded)
                binding = Binding(record["key"], body["parent"]["page_id"], record["title"], record["payload"])
                if (type(record["adapter_schema"]) is not int or record["adapter_schema"] != 1
                        or record["synthetic"] is not True or record["payload_sha256"] != binding.payload_sha256
                        or body != create_body(binding)):
                    raise ValueError()
            except Exception:
                raise GatewayError("POST does not match canonical synthetic create contract") from None
            return "create", None
        match = re.fullmatch(r"/(pages|blocks)/([0-9a-fA-F-]+)(/children)?", path)
        if method != "GET" or body is not None or not match:
            raise GatewayError("Method or endpoint outside gateway scope")
        family, identifier, suffix = match.groups()
        identifier = uuid_key(identifier)
        if family == "pages" and suffix is None and query is None:
            if identifier == self.root or identifier in self._children:
                return "metadata", identifier
        if family == "blocks" and suffix == "/children" and isinstance(query, dict):
            if (set(query) <= {"page_size", "start_cursor"} and type(query.get("page_size")) is int
                    and 1 <= query["page_size"] <= 100
                    and ("start_cursor" not in query or isinstance(query["start_cursor"], str)
                         and 0 < len(query["start_cursor"]) <= 1024)
                    and (identifier == self.root or identifier in self._validated)):
                return "blocks", identifier
        raise GatewayError("Page not discovered under root or metadata not validated")

    def _observe(self, kind, identifier, data):
        if kind == "metadata":
            if data.get("object") != "page" or uuid_key(data["id"]) != identifier:
                raise GatewayError("Metadata identity mismatch")
            if identifier != self.root:
                parent = data.get("parent", {})
                if parent.get("type") != "page_id" or uuid_key(parent["page_id"]) != self.root:
                    raise GatewayError("Discovered page no longer has test-root parent")
                self._validated.add(identifier)
        elif kind == "blocks" and identifier == self.root:
            if data.get("object") != "list" or not isinstance(data.get("results"), list):
                raise GatewayError("Malformed root child enumeration")
            for block in data["results"]:
                if block.get("type") == "child_page":
                    self._children.add(uuid_key(block["id"]))
        elif kind == "create":
            if data.get("object") != "page":
                raise GatewayError("Create outcome lacks page identity")
            self._children.add(uuid_key(data["id"]))

    def __call__(self, method, path, *, query=None, body=None, headers=None):
        # Validate before obtaining a secret or opening a socket.
        try:
            kind, identifier = self._authorize(method, path, query, body, headers)
        except GatewayError:
            raise
        except Exception:
            raise GatewayError("Invalid gateway request shape") from None
        if self.enabled is not True:
            raise GatewayError("Live network execution is disabled")
        if self._requests >= 200 or time.monotonic() >= self._deadline:
            raise GatewayError("Gateway session budget exhausted")
        self._requests += 1
        if kind == "metadata":
            self._validated.discard(identifier)
        connection = None
        try:
            token = self._token_provider()
            if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{16,4096}", token):
                raise GatewayError("Credential provider returned an invalid credential")
            payload = None if body is None else json.dumps(body, ensure_ascii=False).encode()
            if payload is not None and len(payload) > 512000:
                raise GatewayError("Request byte limit exceeded")
            target = "/v1" + path + ("?" + urlencode(query) if query else "")
            request_headers = {"Authorization": "Bearer " + token,
                               "Notion-Version": API_VERSION, "Content-Type": "application/json"}
            connection = self._factory("api.notion.com", port=443, timeout=10,
                                       context=ssl.create_default_context())
            connection.request(method, target, body=payload, headers=request_headers)
            response = connection.getresponse()
            # HTTPSConnection does not follow redirects. No status is retried.
            if response.status != 200:
                raise GatewayError("HTTP status " + str(response.status) + "; no retry attempted")
            chunks, size = [], 0
            while True:
                if time.monotonic() >= self._deadline:
                    raise GatewayError("Gateway session deadline reached during response")
                chunk = response.read1(min(65536, 1048577 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > 1048576:
                    raise GatewayError("Response byte limit exceeded")
            data = json.loads(b"".join(chunks))
            if not isinstance(data, dict) or data.get("object") == "error":
                raise GatewayError("Unsuccessful JSON response")
            self._observe(kind, identifier, data)
            return data
        except GatewayError:
            raise
        except Exception:
            # Do not expose response bodies, request headers or injected errors.
            raise GatewayError("Request failed; outcome may be uncertain; no retry attempted") from None
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
