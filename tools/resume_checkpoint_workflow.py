"""Opt-in, read-only workflow entrypoint for an enrolled Nexus checkpoint.

Invoke explicitly with operator-provided files and validated host assertions.
This script never talks to providers, schedules work, or executes a stage.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nexus_sandbox.resume_decision import decide_resume


def evaluate(binding, checkpoint, inventory_complete, authority_verified):
    decision = decide_resume(checkpoint, binding,
                             inventory_complete=inventory_complete,
                             authority_verified=authority_verified)
    return dict(status=decision.status, completed=list(decision.completed),
                pending=decision.pending, next_action=decision.next_action,
                reason=decision.reason, automatic_execution=False,
                provider_writes=0, cp09='NOT_PROVEN')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', type=Path, required=True,
                        help='Trusted job binding JSON file (not checkpoint-derived)')
    parser.add_argument('--checkpoint', type=Path, required=True,
                        help='Independently observed checkpoint JSON file')
    parser.add_argument('--inventory-complete', action='store_true',
                        help='Host asserts complete observation of the enrolled checkpoint')
    parser.add_argument('--authority-verified', action='store_true',
                        help='Host asserts fresh authorized identity and authority')
    args = parser.parse_args(argv)
    try:
        # No filename, host configuration, or untrusted checkpoint data appears in errors.
        if args.binding.stat().st_size > 65536 or args.checkpoint.stat().st_size > 1048576:
            raise ValueError('oversized input')
        binding = json.loads(args.binding.read_text(encoding='utf-8'))
        checkpoint = args.checkpoint.read_text(encoding='utf-8')
        result = evaluate(binding, checkpoint, args.inventory_complete,
                          args.authority_verified)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        result = dict(status='BLOCKED', completed=[], pending=None,
                      next_action='INVESTIGATE_CHECKPOINT',
                      reason='Input unavailable or malformed; no action permitted',
                      automatic_execution=False, provider_writes=0,
                      cp09='NOT_PROVEN')
    print(json.dumps(result, sort_keys=True))
    # This entrypoint never performs an effect. A ready decision is not a run approval.
    return 0 if result['status'] == 'COMPLETE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
