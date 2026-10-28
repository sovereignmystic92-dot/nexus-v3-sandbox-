"""Read-only bridge for a bounded Notion connector page export.

The injected fetch callable returns a decoded Notion fetch document, not a raw
MCP envelope. No credential lookup or mutation methods are exposed. Exact hash
verification remains required after parsing; rendered text is not original audio.
"""
import re
from uuid import UUID

from .record_readback import Observation


class IncompleteExport(ValueError):
    pass


def parse_page(document, requested_id, *, payload_heading=None):
    if (type(document) is not dict
            or document.get('metadata', {}).get('type') != 'page'
            or document.get('truncated')
            or document.get('unknown_block_count')
            or document.get('unknown_block_ids')):
        raise IncompleteExport('Unsupported or incomplete page export')
    record_id = UUID(document['id']).hex
    if record_id != UUID(requested_id).hex:
        raise IncompleteExport('Fetch returned another page')
    text = document.get('text')
    if not isinstance(text, str) or '<unknown ' in text:
        raise IncompleteExport('Missing or unknown rendered blocks')
    opening = '\n<content>\n'
    closing = '\n</content>\n</page>'
    if text.count(opening) != 1 or text.count(closing) != 1:
        raise IncompleteExport('Ambiguous content envelope')
    header, remainder = text.split(opening, 1)
    if closing not in remainder or remainder.split(closing, 1)[1].strip():
        raise IncompleteExport('Misordered content envelope')
    # Anchor structural tags to full lines, and reject ambiguous envelopes.
    roots = re.findall(r'^<page url="https://app\.notion\.com/p/([0-9a-f-]+)"[^>]*>$',
                       text, re.MULTILINE)
    ancestry = re.findall(r'^<ancestor-path>\n([\s\S]*?)\n</ancestor-path>$',
                          header, re.MULTILINE)
    if len(roots) != 1 or UUID(roots[0]).hex != record_id or len(ancestry) != 1:
        raise IncompleteExport('Ambiguous page identity or ancestry')
    parents = re.findall(r'^<parent-page url="https://app\.notion\.com/p/([0-9a-f-]+)"[^>]*\s*/>$',
                         ancestry[0], re.MULTILINE)
    if len(parents) != 1:
        raise IncompleteExport('One observed direct page parent required')
    opening = '\n<content>\n'
    closing = '\n</content>\n</page>'
    if text.count(opening) != 1 or text.count(closing) != 1:
        raise IncompleteExport('Ambiguous content envelope')
    body = text.split(opening, 1)[1].split(closing, 1)[0]
    if payload_heading is not None:
        if not isinstance(payload_heading, str) or not payload_heading:
            raise ValueError('Nonempty exact heading required')
        marker = payload_heading + '\n\n'
        if body.count(marker) != 1:
            raise IncompleteExport('Missing or ambiguous raw payload heading')
        body = body.split(marker, 1)[1]
    return Observation(record_id, UUID(parents[0]).hex, body, True)


class NotionRecordReader:
    """Callback adapter; no claims of independent provider authentication.

    Payload selection is deliberately bounded: whole rendered content or one
    exact heading to the end. Unsupported layouts hold rather than normalize.
    Metadata omission is not a service completeness attestation. A matching
    expected digest establishes only the selected payload's exact preservation.
    """
    def __init__(self, fetch, *, payload_heading=None):
        self.fetch = fetch
        self.payload_heading = payload_heading

    def __call__(self, record_id):
        return parse_page(self.fetch(record_id), record_id,
                          payload_heading=self.payload_heading)

