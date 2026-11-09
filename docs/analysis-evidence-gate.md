# Structural analysis evidence gate

This opt-in code implements the checkable portion of the existing Domain Quality
Lock and source/output completion rules. It creates no new policy or semantic
quality standard. It neither runs Gemini nor activates a workflow/provider.

Use `processing_pipeline.run_quality_checked` instead of `run` when a trusted host
can provide a complete source/output binding, an independently assessed tuple of
materially relevant domain names, and a fresh evidence reader. The original
non-resumable runner remains available; this change does not silently claim
mandatory coverage for existing callers.

The binding has exactly run_id, source_id, source_sha256, output_id and
output_sha256. Digests are exact lowercase SHA-256 values. An evidence report has
schema=nexus.analysis-evidence.v1, that exact binding, output_text, and domains.

Each domain has exactly name plus the existing seven determinations: relevance,
contribution, knowledge_impact, full_potential, required_action, questions and
verification. Textual determinations must be nonempty; no question is a valid
finding only when the caller explicitly records that determination.
required_action has status, reason, evidence_refs. A needed action must be
VERIFIED with nonempty references. NOT_REQUIRED needs an explicit reason.
PENDING, BLOCKED and deferred required actions cannot pass. Optional research
questions remain distinct from required unfinished processing actions.
verification has status=VERIFIED and nonempty evidence_refs.

The guard checks the exact host-declared domain set (including omission and
duplicate detection), run/source/output bindings, actual supplied output-text
digest, complete determinations and action/verification dispositions before
calling PERSISTED. Missing evidence prevents that provider-effect stage and all
dependent stages. After the original READBACK_VERIFIED callback, the host must
supply a new POST_READBACK report; its canonical evidence hash must match the
pre-persistence report. Changed content, source, disposition or evidence blocks
COMPLETE and retains REGISTERED as the last confirmed checkpoint. A report
digest is included in persistence/final receipts and their existing checkpoint
readbacks. No retry or repair is attempted.

The reader receives PRE_PERSISTENCE or POST_READBACK. It must return candidate
evidence for the first, actual independently fetched saved output/report for the
second. Returning the same cached object is not independent readback. This
library cannot authenticate a callback or establish freshness from its existence.
The host owns evidence custody, provider grants, account/parent identity, source
acquisition, actual relevance assessment and report-to-rendered-output mapping.

**Limits:** a nonempty determination is not proof of useful analysis. An evidence
reference is not source authentication, factual corroboration, an independent
review, or confirmation that the named action occurred. The actual output-text
hash prevents stale text being accepted as the pinned text, but does not prove
that domain metadata accurately describes that text. No universal semantic
hyperlink verifier, knowledge-promotion evaluator, remote fence, resumable-host
integration or mandatory Chat invocation is installed.

Run the focused suite with:
`PYTHONPATH=src python -m unittest discover -s tests/unit -p 'test_analysis_evidence.py' -v`.
Existing processing-pipeline tests must also pass. Provider-level acceptance and
independent review remain separate. On an uncertain outcome, inspect the retained
checkpoint and actual destination; do not rerun the non-resumable flow blindly.
Rollback is reverting these source/test/doc changes; retain real receipts.

## Supervised live-host preparation

The existing `execute_supervised` now optionally accepts `analysis_gate` with
exactly binding, required_domains (tuple), and report. The gate binding's
source_id/source_sha256 must match the exact Notion source; output_id is the
pinned Cortex destination **name**, while the existing host separately verifies
native module ID, owner, version and complete content. The report output_text
must be the exact saved content, including the host's NEXUS_SOURCE_PAGE and
NEXUS_SOURCE_SHA256 prefix lines. Its SHA-256 is the binding's output_sha256.

The gate is validated before any provider request. Its report fingerprint becomes
part of the same existing durable execution journal binding. Changing or removing
the gate, changing its assessed domains/evidence, or adding it to an older
ungated journal fails binding before provider access. Do not discard/reset a
journal to bypass this hold; new read-only assessment work needs a separately
named, declared test transaction after checking the existing output.

Every actual cortex_get callback then validates the report against the freshly
returned provider content before the journal can reach VERIFIED. An unsuccessful
handoff reports PRECHECK_ONLY; only a matched readback reports
STRUCTURAL_READBACK_MATCHED. The latter remains structural evidence, not factual
or independent-review acceptance. The assessment is pinned in journal metadata;
the host remains responsible for ensuring it accurately describes the saved
analysis and for separately persisting/readback-verifying the receipt.

Existing CLI configuration remains unchanged and does not accept this sidecar.
A supervised Chat Python host can invoke the API directly with its authenticated
request callback. No provider credentials enter the code or sidecar. This prepares
a bounded test when the owner supplies a new transcript; it is not a standing
auto-ingestion installation or permission to generate missing evidence.

The already scheduled November 9 pilot has a separate gate-assessment instruction:
inspect the exact checked candidate first, exercise only the authorized read-only
scope when supported, or record BLOCKED/NOT_TESTED and continue its original
checkpoint-resume test. The pilot must not rewrite the existing analysis to pass
the gate or count its replay as a fresh qualifying ingestion.
