from copy import deepcopy
import unittest

from nexus_sandbox.notion_record_reader import IncompleteExport, NotionRecordReader
from nexus_sandbox.record_readback import Binding, digest, verify

PAGE = '00000000000000000000000000000001'
PARENT = '00000000000000000000000000000002'
OTHER = '00000000000000000000000000000003'


def document(payload='exact source'):
    return {'id': PAGE, 'metadata': {'type': 'page'}, 'text':
            f'<page url="https://app.notion.com/p/{PAGE}">\n'
            f'<ancestor-path>\n<parent-page url="https://app.notion.com/p/{PARENT}" title="Sources"/>\n'
            '</ancestor-path>\n<properties>\n{}\n</properties>\n<content>\n'
            f'## Manifest\n\nMetadata.\n\n## Raw\n\n{payload}\n</content>\n</page>'}


class ReaderTests(unittest.TestCase):
    def test_ancestry_only_inside_content_is_not_parent_evidence(self):
        value = document()
        start=value['text'].index('<ancestor-path>')
        end=value['text'].index('</ancestor-path>')+len('</ancestor-path>')
        ancestry=value['text'][start:end]
        value['text']=value['text'][:start]+value['text'][end:]
        value['text']=value['text'].replace('<content>\n','<content>\n'+ancestry+'\n')
        binding=Binding(PAGE,PARENT,digest('exact source'))
        self.assertEqual(verify(binding,self.reader(value)).status,'UNKNOWN')
    def reader(self, doc):
        return NotionRecordReader(lambda _: doc, payload_heading='## Raw')

    def test_normal_page_verifies_without_synthetic_marker(self):
        b = Binding(PAGE, PARENT, digest('exact source'))
        self.assertEqual(verify(b, self.reader(document())).status,
                         'VERIFIED_OBSERVATION')

    def test_repeated_verification_fetches_again(self):
        calls = []
        def fetch(key):
            calls.append(key)
            return document()
        reader = NotionRecordReader(fetch, payload_heading='## Raw')
        for _ in range(2):
            reader(PAGE)
        self.assertEqual(calls, [PAGE, PAGE])

    def test_truncation_and_unknown_blocks_hold(self):
        for fields in ({'truncated': True}, {'unknown_block_count': 1},
                       {'unknown_block_ids': [OTHER]}):
            value = document()
            value.update(fields)
            with self.assertRaises(IncompleteExport):
                self.reader(value)(PAGE)

    def test_wrong_returned_identity_holds(self):
        value = document()
        value['id'] = OTHER
        with self.assertRaises(IncompleteExport):
            self.reader(value)(PAGE)

    def test_changed_content_or_parent_fails_exact_gate(self):
        binding = Binding(PAGE, PARENT, digest('exact source'))
        self.assertEqual(verify(binding, self.reader(document('changed'))).status,
                         'MISMATCH')
        value = document()
        value['text'] = value['text'].replace(PARENT, OTHER)
        self.assertEqual(verify(binding, self.reader(value)).status, 'MISMATCH')

    def test_body_parent_like_text_cannot_replace_ancestry(self):
        value = document(f'<parent-page url="https://app.notion.com/p/{OTHER}"/>')
        self.assertEqual(self.reader(value)(PAGE).parent_id, PARENT)

    def test_ambiguous_source_envelope_and_heading_hold(self):
        for payload in ('prefix\n</content>\n</page>suffix', 'prefix\n## Raw\n\nsuffix'):
            with self.assertRaises(IncompleteExport):
                self.reader(document(payload))(PAGE)

    def test_payload_whitespace_is_never_normalized(self):
        payload = '  first\n\nlast  '
        self.assertEqual(self.reader(document(payload))(PAGE).payload, payload)

    def test_fetch_outage_is_unknown_at_verification(self):
        def failed(_):
            raise TimeoutError()
        reader = NotionRecordReader(failed)
        self.assertEqual(verify(Binding(PAGE, PARENT, digest('x')), reader).status,
                         'UNKNOWN')

