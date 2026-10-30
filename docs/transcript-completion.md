# Transcript completion checks

Status: implemented opt-in library, pending review and live integration.

`transcript_completion.run_transcript` wraps the existing seven-stage processing
pipeline. It compares every ordered source segment after preservation, before
analysis can begin, and fetches/comparisons again before final completion. Each
declared linked output must match the exact source ID, source text digest,
canonical output parent and structured `ARCHIVED` source status. A failed or
unavailable read blocks completion and preserves the existing pipeline checkpoint.
These checks make a supplied excerpt incapable of matching an expected full input.

The caller supplies the full trusted input, exact canonical parent/page IDs, and
fresh read-only callbacks returning fully paginated snapshots. Provider markup
must be decoded losslessly; this library does not guess at markup normalization.
Segment identity, boundaries and order are part of the comparison. A complete
supplied transcript is not necessarily a complete transcript of the original audio.

The existing pipeline remains unchanged. Callers must opt into this wrapper.
There is no connector parser, service listener, write transport, installed workflow
or chat-wide routing enforcement here. An untrusted callback can lie. The expected
output inventory is caller-supplied; discovery of omitted backlinks is not proven.
Structured archival status is checked, but contradictions in free prose need a
separate reconciler. Historical accuracy, semantic analysis depth, editorial-copy
accuracy, CP05, authorization and remote fencing are not established by this gate.
The gate grants no write permission and makes no checkpoint-score changes.

The wrapper uses the existing non-resumable runner; do not blindly rerun effects
after a hold. Inspect the last confirmed checkpoint and reconcile uncertain work
before arranging the next invocation. General resumable integration remains future
work, as does durable custody independent of a caller's checkpoint storage.

## Validation

Run `PYTHONPATH=src python3 -m unittest discover -s tests/unit -p test_transcript_completion.py -v`.
Tests use only synthetic text and IDs. They cover interior mutation with equal word
count, missing/reordered/duplicated segments, changed boundaries, wrong placement,
stale output status/hash/link, incomplete reads, source changes after analysis,
checkpoint failure and successful pipeline integration with two source fetches.
The existing `tools/validate.py` automatically discovers this test module.

## Remaining integration

Provide a reviewed connector-backed snapshot parser, trusted input/enrollment and
complete output discovery; implement targeted prose-status reconciliation and
durable resume; route an explicitly enrolled real transaction through the wrapper;
verify the actual completion boundary cannot bypass it. Until then, the library
is executable and locally testable but live enforcement is not installed.
