"""Bounded GitHub text-log decoding; no transport, credentials or execution."""
import re

from ci_failure_evidence import extract_cases, require

TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z (.*)$')
COLOR = re.compile(r'\x1b\[[0-9;]*m')


def extract_github_cases(log):
    """Decode one complete timestamped job log containing one unittest suite.

    Each nonempty line must have GitHub's UTC prefix. Only ANSI SGR colors are
    stripped; other control sequences, partial or multiple suites hold. The host
    must authenticate and bind the complete response to its exact job/attempt.
    """
    require(type(log) is str and len(log.encode('utf-8')) <= 2 * 1024 * 1024)
    # The downloaded GitHub text response can begin with a UTF-8 BOM.
    if log.startswith('\ufeff'):
        log = log[1:]
    lines = []
    for raw in log.replace('\r\n', '\n').split('\n'):
        if not raw:
            continue
        match = TIMESTAMP.fullmatch(raw)
        if match is None:
            return []
        line = COLOR.sub('', match[1])
        if any(ord(c) < 32 and c != '\t' for c in line) or '\x7f' in line:
            return []
        lines.append(line)
    return extract_cases('\n'.join(lines) + '\n')
