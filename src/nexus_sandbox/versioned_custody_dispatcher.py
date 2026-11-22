"""Map trusted versioned-file operations to the supervised custody ports.

No SDK, credentials, endpoint or retries. The authenticated host implements the
three exact operations; optimistic replacement must be atomic at the service.
"""
import base64
import json

from .supervised_journal_custody import JournalCustody, _head, _text
from .transcript_supervised_cli import _decode

MAX_CONTENT = 512 * 1024
HEAD_SCHEMA = 'nexus.versioned-custody-head.v1'


def _bytes(value):
    if type(value) is not str or len(value) > ((MAX_CONTENT + 2) // 3) * 4:
        raise ValueError('Bounded base64 storage content required')
    raw = base64.b64decode(value, validate=True)
    if not 0 < len(raw) <= MAX_CONTENT:
        raise ValueError('Bounded storage content required')
    return raw


def _encoded(content):
    if type(content) is not bytes or not 0 < len(content) <= MAX_CONTENT:
        raise ValueError('Bounded exact storage bytes required')
    return base64.b64encode(content).decode('ascii')


class VersionedCustodyDispatcher:
    """One pinned key/head-reference mapping, supplied by the authorized host.

    request(store_create, {content_b64}) -> {reference}
    request(store_read, {reference}) -> {reference, version, content_b64}
    request(store_replace, {reference, expected_current_version, content_b64})
        -> {status: UPDATED, reference, version} OR {status: CONFLICT}

    Errors/timeouts must raise. An ambiguous replacement is not a conflict or
    permission to retry. Only the pinned head can be replaced; retained objects
    are create/read only. No key discovery or head bootstrap is provided.
    """

    def __init__(self, key, head_reference, request):
        if not _text(key) or not _text(head_reference) or not callable(request):
            raise ValueError('Pinned key, head identity and trusted dispatcher required')
        self.key, self.head_reference, self.request = key, head_reference, request

    def _read(self, reference):
        if not _text(reference):
            raise ValueError('Exact private storage identity required')
        result = self.request('store_read', dict(reference=reference))
        if (type(result) is not dict or set(result) != {'reference', 'version', 'content_b64'}
                or result['reference'] != reference or type(result['version']) is not int
                or result['version'] < 0):
            raise ValueError('Storage read identity/version mismatch')
        return _bytes(result['content_b64']), result['version']

    def _document(self, key):
        if key != self.key:
            raise ValueError('Custody key changed')
        content, version = self._read(self.head_reference)
        doc = _decode(content)
        if (type(doc) is not dict or set(doc) != {'schema', 'key', 'head'}
                or doc['schema'] != HEAD_SCHEMA or doc['key'] != self.key):
            raise ValueError('Pinned head document mismatch')
        _head(doc['head'])
        return doc, version

    def head(self, key):
        return self._document(key)[0]['head']

    def retain(self, content):
        result = self.request('store_create', dict(content_b64=_encoded(content)))
        if (type(result) is not dict or set(result) != {'reference'}
                or not _text(result['reference']) or result['reference'] == self.head_reference):
            raise ValueError('Retained-object identity required')
        return result['reference']

    def read(self, reference):
        if reference == self.head_reference:
            raise ValueError('Head document cannot serve as retained journal')
        return self._read(reference)[0]

    def cas(self, key, expected, new):
        _head(expected)
        _head(new)
        if (new is None or new['reference'] == self.head_reference
                or new['generation'] != (1 if expected is None else expected['generation'] + 1)):
            raise ValueError('Next custody generation required')
        doc, version = self._document(key)  # Fresh read; never cached version.
        if doc['head'] != expected:
            return False
        content = json.dumps(dict(schema=HEAD_SCHEMA, key=self.key, head=new),
            sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        result = self.request('store_replace', dict(reference=self.head_reference,
            expected_current_version=version, content_b64=_encoded(content)))
        if type(result) is dict and result == {'status': 'CONFLICT'}:
            return False
        if (type(result) is not dict or set(result) != {'status', 'reference', 'version'}
                or result['status'] != 'UPDATED' or result['reference'] != self.head_reference
                or type(result['version']) is not int or result['version'] != version + 1):
            raise ValueError('Uncertain storage replacement; reconcile without retry')
        return True  # JournalCustody independently re-reads pointer and object.

    def custody(self, binding):
        return JournalCustody(self.key, binding, retain=self.retain, read=self.read,
                              head=self.head, cas=self.cas)
