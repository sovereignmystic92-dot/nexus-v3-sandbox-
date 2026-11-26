"""Private single-transcript custody IPC; authenticated ports remain host-owned."""
import argparse
import json
import sys

from .supervised_journal_custody import expected_binding, execute_custodied_supervised
from .transcript_supervised_cli import LIMIT, FIELDS, _decode, _read_line
from .versioned_custody_dispatcher import VersionedCustodyDispatcher

OPERATIONS = frozenset(('store_create', 'store_read', 'store_replace',
                        'archive_read', 'cortex_get', 'cortex_create'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--journal', required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--initialize', action='store_true')
    mode.add_argument('--restore', action='store_true')
    parser.add_argument('--allow-create', action='store_true')
    args = parser.parse_args(argv)
    counter = 0

    def emit(value):
        raw = json.dumps(value, allow_nan=False, separators=(',', ':'))
        if len(raw.encode()) > LIMIT:
            raise ValueError('Bounded private IPC required')
        print(raw, flush=True)

    def request(operation, payload):
        nonlocal counter
        if operation not in OPERATIONS:
            raise ValueError('Unknown operation')
        counter += 1
        emit(dict(type='request', id=counter, operation=operation, payload=payload))
        reply = _decode(_read_line(sys.stdin.fileno()))
        if (type(reply) is not dict or set(reply) != {'id', 'ok', 'value'}
                or type(reply['id']) is not int or reply['id'] != counter
                or reply['ok'] is not True):
            raise ValueError('Failed/unbound host response')
        return reply['value']

    try:
        with open(args.config, 'rb') as stream:
            raw = stream.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('Bounded configuration required')
        config = _decode(raw)
        if (type(config) is not dict or set(config) !=
                {'supervised', 'custody_key', 'custody_head_reference'}):
            raise ValueError('Exact single-transcript configuration required')
        supervised = config['supervised']
        if type(supervised) is not dict or set(supervised) != FIELDS | {'analysis_gate'}:
            raise ValueError('Exact supervised configuration required')
        gate = supervised['analysis_gate']
        if (type(gate) is not dict or set(gate) != {'binding', 'required_domains', 'report'}
                or type(gate['required_domains']) is not list):
            raise ValueError('Complete JSON analysis gate required')
        gate['required_domains'] = tuple(gate['required_domains'])
        binding = expected_binding(supervised)
        desired = ('NEXUS_SOURCE_PAGE=' + supervised['source_page'] + '\nNEXUS_SOURCE_SHA256='
                   + supervised['source_sha256'] + '\n' + supervised['analysis'])
        if (gate['binding']['source_id'] != supervised['source_page']
                or gate['binding']['source_sha256'] != supervised['source_sha256']
                or gate['binding']['output_id'] != supervised['output_name']
                or gate['report']['output_text'] != desired):
            raise ValueError('Gate must bind exact operation before storage access')
        adapter = VersionedCustodyDispatcher(config['custody_key'],
                                             config['custody_head_reference'], request)
        custody = adapter.custody(binding)
        if args.restore:
            if args.allow_create:
                raise ValueError('Restore is read-only reconciliation')
            custody.restore(args.journal)
        result = execute_custodied_supervised(custody=custody,
            initialize=args.initialize, **supervised, journal_path=args.journal,
            request=request, allow_create=args.allow_create)
        # This entrypoint verifies output/journal, not downstream receipt custody.
        matched = (result['execution']['handoff']['status'] == 'READBACK_MATCHED'
                   and result['execution'].get('analysis_evidence_status') ==
                   'STRUCTURAL_READBACK_MATCHED')
        emit(dict(type='result', result=result, transaction_complete=False,
                  next_action=('RETAIN_AND_INDEPENDENTLY_READ_EXECUTION_RECEIPT'
                               if matched else 'RECONCILE_NO_BLIND_RETRY')))
        return 0 if matched else 2
    except Exception:
        print('{"type":"blocked","next_action":"RECONCILE_NO_BLIND_RETRY",'
              '"transaction_complete":false}', flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
