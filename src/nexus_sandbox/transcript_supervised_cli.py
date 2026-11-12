"""Private JSON-lines host protocol. No provider SDK, credentials or network."""
import argparse
import json
import os
import select
import sys
import time

from .transcript_supervised_host import execute_supervised, reconcile_legacy_supervised


LIMIT = 1024 * 1024
FIELDS = {'prepared', 'source_page', 'source_sha256', 'output_name',
          'analysis', 'expected_owner'}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _decode(raw):
    def invalid_constant(value):
        raise ValueError('nonfinite JSON')
    return json.loads(raw, object_pairs_hook=_object,
                      parse_constant=invalid_constant)


def _read_line(fd, timeout=45):
    deadline = time.monotonic() + timeout
    raw = bytearray()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise TimeoutError('complete host response deadline exceeded')
        part = os.read(fd, min(65536, LIMIT + 1 - len(raw)))
        if not part:
            raise ValueError('host response EOF')
        raw.extend(part)
        if len(raw) > LIMIT:
            raise ValueError('oversized host response')
        if b'\n' in raw:
            if raw.count(b'\n') != 1 or not raw.endswith(b'\n'):
                raise ValueError('unsolicited response data')
            return bytes(raw)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--journal', required=True)
    parser.add_argument('--allow-create', action='store_true')
    parser.add_argument('--reconcile-legacy-reason')
    parser.add_argument('--reconcile-legacy-evidence')
    args = parser.parse_args(argv)
    counter = 0

    def emit(value):
        raw = json.dumps(value, allow_nan=False, separators=(',', ':'))
        if len(raw.encode('utf-8')) > LIMIT:
            raise ValueError('protocol message too large')
        print(raw, flush=True)

    def request(operation, payload):
        nonlocal counter
        if operation not in ('archive_read', 'cortex_get', 'cortex_create'):
            raise ValueError('unknown operation')
        counter += 1
        emit(dict(type='request', id=counter, operation=operation, payload=payload))
        raw = _read_line(sys.stdin.fileno())
        response = _decode(raw)
        if (not isinstance(response, dict)
                or set(response) != {'id', 'ok', 'value'}
                or type(response['id']) is not int or response['id'] != counter
                or response['ok'] is not True):
            raise ValueError('failed or unbound host response')
        return response['value']

    try:
        with open(args.config, 'rb') as stream:
            raw = stream.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('config too large')
        config = _decode(raw)
        legacy = (args.reconcile_legacy_reason is not None
                  or args.reconcile_legacy_evidence is not None)
        expected_fields = FIELDS if legacy else FIELDS | {'analysis_gate'}
        if type(config) is not dict or set(config) != expected_fields:
            raise ValueError('unexpected config fields')
        if legacy:
            if args.allow_create:
                raise ValueError('legacy reconciliation cannot create')
            result = reconcile_legacy_supervised(journal_path=args.journal,
                request=request, reason=args.reconcile_legacy_reason,
                evidence_ref=args.reconcile_legacy_evidence, **config)
        else:
            gate = config['analysis_gate']
            if (type(gate) is not dict or set(gate) !=
                    {'binding', 'required_domains', 'report'}
                    or type(gate['required_domains']) is not list):
                raise ValueError('exact JSON analysis gate required')
            gate['required_domains'] = tuple(gate['required_domains'])
            result = execute_supervised(journal_path=args.journal, request=request,
                                        allow_create=args.allow_create, **config)
        emit(dict(type='result', result=result))
        return 0 if result['handoff']['status'] == 'READBACK_MATCHED' else 2
    except Exception:
        # Provider errors and private payloads must not leak into public logs.
        print('{"type":"blocked","next_action":"RECONCILE_NO_BLIND_RETRY",'
              '"audit_promotion":false}', flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
