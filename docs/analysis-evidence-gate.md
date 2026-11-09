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
