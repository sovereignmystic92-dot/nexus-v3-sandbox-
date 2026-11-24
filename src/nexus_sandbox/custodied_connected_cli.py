"""Private connected-custody JSON-lines protocol; no network or credentials.

Only the authenticated host may service requests. Never send this IPC to public
logs: journal envelopes can contain complete source text in native bindings.
"""
import argparse
import json
import sys

from .source_connection_plan import validate_connection_plan
from .supervised_journal_custody import expected_binding, execute_custodied_connected
from .transcript_supervised_cli import LIMIT, FIELDS, _decode, _read_line
from .versioned_custody_dispatcher import VersionedCustodyDispatcher, _bytes

OPERATIONS = frozenset(('store_create', 'store_read', 'store_replace',
    'archive_read', 'cortex_get', 'cortex_create', 'source_reference', 'retained_receipt'))


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
        content = json.dumps(value, allow_nan=False, separators=(',', ':'))
        if len(content.encode()) > LIMIT:
            raise ValueError('Bounded private IPC required')
        print(content, flush=True)

    def request(operation, payload):
        nonlocal counter
        if operation not in OPERATIONS:
            raise ValueError('Unknown private operation')
        counter += 1
        emit(dict(type='request', id=counter, operation=operation, payload=payload))
        response = _decode(_read_line(sys.stdin.fileno()))
        if (type(response) is not dict or set(response) != {'id', 'ok', 'value'}
                or type(response['id']) is not int or response['id'] != counter
                or response['ok'] is not True):
            raise ValueError('Failed/unbound host response')
        return response['value']

    try:
        with open(args.config, 'rb') as stream:
            raw = stream.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('Bounded configuration required')
        config = _decode(raw)
        if (type(config) is not dict or set(config) !=
                {'plan', 'consumer', 'supervised', 'custody_head_reference'}):
            raise ValueError('Exact connected custody configuration required')
        validate_connection_plan(config['plan'])
        entries = [entry for entry in config['plan']['consumers']
                   if entry['consumer'] == config['consumer']]
        if len(entries) != 1:
            raise ValueError('Planned consumer required')
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
                or gate['binding']['run_id'] != config['plan']['mission_id']
                or gate['report']['output_text'] != desired):
            raise ValueError('Gate must bind exact operation before storage access')
        source = config['plan']['source']
        if (source['document_id'] != 'notion:' + supervised['source_page']
                or source['source_sha256'] != supervised['source_sha256']):
            raise ValueError('Plan must bind supervised source before storage access')
        adapter = VersionedCustodyDispatcher(entries[0]['work_key'],
                                             config['custody_head_reference'], request)
        custody = adapter.custody(binding)
        if args.restore:
            if args.allow_create:
                raise ValueError('Restore is read-only reconciliation')
            custody.restore(args.journal)

        def receipt_reader(work_key):
            value = request('retained_receipt', dict(work_key=work_key))
            if value is None:
                return None
            if type(value) is not dict or set(value) != {'reference', 'content_b64'}:
                raise ValueError('Exact retained receipt response required')
            return dict(reference=value['reference'], content=_bytes(value['content_b64']))

        result = execute_custodied_connected(custody=custody, plan=config['plan'],
            consumer=config['consumer'], initialize=args.initialize,
            supervised_kwargs=dict(supervised, journal_path=args.journal,
                request=request, allow_create=args.allow_create),
            read_source_reference=lambda document_id: request('source_reference',
                dict(document_id=document_id)), read_retained_receipt=receipt_reader)
        emit(dict(type='result', result=result))
        return 0 if result['execution']['status'] == 'CONSUMER_PERSISTENCE_READBACK_MATCHED' else 2
    except Exception:
        print('{"type":"blocked","next_action":"RECONCILE_NO_BLIND_RETRY",'
              '"audit_promotion":false}', flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
