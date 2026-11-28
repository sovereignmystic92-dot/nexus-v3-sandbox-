"""Synthetic HTTP socket faults; no external provider or real credentials.

Only this test's opener routes fixed-origin requests to numeric loopback. The
production BoundClient keeps its pinned HTTPS origin and 20-second deadline.
"""
import copy
import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import sqlite3
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
from uuid import uuid4


spec = importlib.util.spec_from_file_location('socket_archive_probe',
    Path(__file__).resolve().parents[2] / 'tools/notion_archive_live_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
DEST = '12345678-1234-1234-1234-123456789abc'


class FixtureServer(ThreadingHTTPServer):
    daemon_threads = False

    def __init__(self, mode):
        super().__init__(('127.0.0.1', 0), FixtureHandler)
        self.mode = mode
        self.lock = threading.Lock()
        self.blocks, self.patch_indices = [], []
        self.release, self.settled = threading.Event(), threading.Event()
        self.fail_reads = False


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, data, status=200):
        raw = json.dumps(data).encode()
        try:
            self.send_response(status)
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Expected when the client times out before this response.

    def do_GET(self):
        if self.path != '/v1/blocks/' + DEST + '/children?page_size=100':
            return self.reply({}, 400)
        with self.server.lock:
            blocks = copy.deepcopy(self.server.blocks)
            failed = self.server.fail_reads
        self.reply({'results': blocks, 'has_more': False}, 503 if failed else 200)

    def do_PATCH(self):
        if self.path != '/v1/blocks/' + DEST + '/children':
            return self.reply({}, 400)
        payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        block = payload['children'][0]
        meta = json.loads(block['code']['caption'][0]['text']['content'])
        index = meta['index']
        block.update(id=str(uuid4()), has_children=False,
                     parent={'type': 'page_id', 'page_id': DEST})
        with self.server.lock:
            self.server.patch_indices.append(index)
            first = len(self.server.patch_indices) == 1
            if not first or self.server.mode == 'committed':
                self.server.blocks.append(block)
        if first:
            # No headers or body until released: a real recv deadline expires.
            # Safety bound prevents an abandoned test from leaving a handler.
            released = self.server.release.wait(5)
            if released and self.server.mode == 'delayed':
                with self.server.lock:
                    self.server.blocks.append(block)
            self.server.settled.set()
        self.reply({'results': [block]})


class LoopbackOpener:
    """Test-only transport seam; never forwards Authorization or proxy settings."""
    def __init__(self, server):
        self.server = server
        self.inner = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), probe.NoRedirect())
        self.timeouts = 0

    def open(self, request, *, timeout):
        parsed = urllib.parse.urlsplit(request.full_url)
        if (parsed.scheme != 'https' or parsed.netloc != 'api.notion.com'
                or request.get_header('Authorization') != 'Bearer synthetic-token'
                or timeout != 20):
            raise AssertionError('unexpected test request or credential')
        url = 'http://127.0.0.1:' + str(self.server.server_port) + parsed.path
        if parsed.query:
            url += '?' + parsed.query
        local = urllib.request.Request(url, data=request.data,
            method=request.get_method(), headers={'Content-Type': 'application/json'})
        try:
            return self.inner.open(local, timeout=0.25)
        except socket.timeout:
            self.timeouts += 1
            raise


class SocketTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.journal = str(Path(self.temporary.name) / 'archive.sqlite')
        self.prepared = probe.prepare_transcript(probe.RAW, 256)
        self.sha = self.prepared['receipt']['sha256']

    def start(self, mode):
        self.server = FixtureServer(mode)
        thread = threading.Thread(target=self.server.serve_forever,
                                  kwargs={'poll_interval': 0.02})
        thread.start()
        def stop():
            self.server.release.set()
            self.server.shutdown()
            self.server.server_close()
            thread.join(2)
            self.assertFalse(thread.is_alive())
        self.addCleanup(stop)

    def ports(self, write=True):
        client = probe.BoundClient(DEST, 'synthetic-token', write)
        client.opener = LoopbackOpener(self.server)
        port = probe.NotionArchivePort(client, self.prepared, DEST,
                                      expected_source_sha256=self.sha)
        return client, port

    def attempt(self, client, port):
        return probe.ArchiveRecoveryHost(self.journal).attempt(
            self.prepared, DEST, expected_source_sha256=self.sha,
            read_archive=port.read_archive, write_chunk=port.write_chunk,
            authorize_write=lambda dest, sha, index:
                dest == DEST and sha == self.sha and 0 <= index < 3)

    def first_timeout(self):
        client, port = self.ports()
        with self.assertRaisesRegex(RuntimeError,
                '^provider request unavailable; reconcile before retry$'):
            self.attempt(client, port)
        self.assertEqual(client.opener.timeouts, 1)
        self.assertEqual(client.writes, 1)
        with sqlite3.connect(self.journal) as db:
            self.assertEqual(db.execute('SELECT state,chunk_index FROM archive_events '
                'ORDER BY id').fetchall(), [('READBACK_REQUIRED', None),
                ('MISSING_CHUNKS', None), ('WRITE_INTENT', 0),
                ('WRITE_OUTCOME_UNKNOWN', 0)])
        # A caught timeout never refreshes the transport's write budget.
        with self.assertRaises(ValueError):
            client.append(block_id=DEST, children=[{}], position={'type': 'start'})
        self.assertEqual(self.server.patch_indices, [0])

    def finish(self):
        for expected in ('MISSING_CHUNKS', 'ARCHIVE_VERIFIED'):
            client, port = self.ports()
            self.assertEqual(self.attempt(client, port)['state'], expected)
            self.assertEqual(client.writes, 1)
        client, port = self.ports(False)
        result = self.attempt(client, port)
        self.assertEqual(result['state'], 'ARCHIVE_VERIFIED')
        self.assertTrue(result['archive_readback_verified'])
        self.assertFalse(result['audit_promotion'])
        self.assertFalse(result['cortex_write_allowed'])
        self.assertEqual(client.writes, 0)
        self.assertEqual(self.server.patch_indices, [0, 1, 2])
        with self.server.lock:
            chunks = [''.join(p['text']['content'] for p in b['code']['rich_text'])
                      for b in self.server.blocks]
        self.assertEqual(chunks, self.prepared['chunks'])
        self.assertEqual(''.join(chunks), probe.RAW)

    def test_committed_write_timeout_reconciles_without_duplicate(self):
        self.start('committed')
        self.first_timeout()
        self.finish()

    def test_uncommitted_timeout_holds_even_after_request_settles(self):
        self.start('uncommitted')
        self.first_timeout()
        self.server.release.set()
        self.assertTrue(self.server.settled.wait(2))
        for _ in range(2):
            client, port = self.ports()
            with self.assertRaisesRegex(ValueError, 'prior write unresolved'):
                self.attempt(client, port)
            self.assertEqual(client.writes, 0)
        self.assertEqual(self.server.patch_indices, [0])
        self.assertEqual(self.server.blocks, [])

    def test_delayed_commit_cannot_be_retried_during_visibility_gap(self):
        self.start('delayed')
        self.first_timeout()
        client, port = self.ports()
        with self.assertRaisesRegex(ValueError, 'prior write unresolved'):
            self.attempt(client, port)
        self.assertEqual(client.writes, 0)
        self.assertEqual(self.server.patch_indices, [0])
        self.server.release.set()
        self.assertTrue(self.server.settled.wait(2))
        self.finish()

    def test_readback_failure_after_timeout_never_authorizes_retry(self):
        self.start('committed')
        self.first_timeout()
        with self.server.lock:
            self.server.fail_reads = True
        client, port = self.ports()
        with self.assertRaisesRegex(RuntimeError, 'reconcile before retry'):
            self.attempt(client, port)
        self.assertEqual(client.writes, 0)
        self.assertEqual(self.server.patch_indices, [0])


if __name__ == '__main__':
    unittest.main()
