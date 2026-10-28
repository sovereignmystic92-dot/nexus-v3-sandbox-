# Real-record readback bridge — draft, not activated

The synthetic coordinator and Cortex adapter retain their fixture-only checks.
This additive verifier applies the same exact identity/content-binding principle
to host-observed real records without granting any mutation capability.

`record_readback.verify` invokes its supplied reader on every call, checks UUID
identity and direct parent, requires explicit boolean completeness, and compares
an independently bound UTF-8 SHA-256. Read failures/incomplete observations hold
as UNKNOWN; identity, location or payload disagreement returns MISMATCH.
VERIFIED_OBSERVATION means only that the supplied observation matches the binding.
The expected digest must come from the intended source, not the observed record.

## Validation

Eight local unit tests passed: exact/repeated reads, wrong identity, moved parent,
single-character corruption, incomplete/malformed observations, read failure,
invalid binding and equivalent UUID formatting.

The code also evaluated a fresh connected-Notion fetch of the owner's existing
transcript: 16,386 supplied characters matched the original intended text. Local
altered-content and wrong-parent copies returned MISMATCH. No remote record was
altered by those negative cases. The host extracted the raw segment and direct
parent from the fetched page; this extraction remains an operator-controlled
boundary, not a hardened Notion export parser. Private page IDs, transcript and
observation files are intentionally excluded from this public change.

No hosted test result is claimed here. No write protection, durable recovery,
duplicate absence, autonomous fetch provenance, source truth, future persistence,
multi-worker safety or full Nexus activation follows from this check. The caller
can still bypass this library; it is not yet mandatory in the execution path.

## Next integration step

Review the existing draft PR #3 rather than recreate its Notion adapter. It has
synthetic-only contracts, JSON fixture layout, complete-child-list requirements
and uncertain-create journaling; those cannot simply be applied to ordinary
Nexus pages. Assess current-main compatibility, typed source/output bindings,
actual connector pagination/completeness, durable journal custody and a bounded
pilot transport before proposing real mutations. Keep its old workflow edits,
test-fixture restrictions and live gateway disabled unless separately reviewed.
The immediate next deliverable is a compatibility decision and minimal adapter
change, with explicit recovery behavior for uncertain writes. No merge or live
write rollout is authorized by this document.
