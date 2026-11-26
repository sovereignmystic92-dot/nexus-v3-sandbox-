# One controlled continuation of a confirmed pre-dispatch INTENT

Candidate implementation/policy for exact review. Preparation authorization does
not authorize using it on the real Tengri journal before approval. No runner,
service, schedule, credential, source writer or new store is installed.

The public native host permits creates only from PREPARED. All recovery callers
use recover_checkpoint_supervised, which combines retained checkpoint evidence
and receipt checks with a private native helper that consumes the exact permit.
Updates and legacy ungated journals cannot use this exception. AGENTS rule12 is
the explicit proposed policy amendment.

## Authority is positive evidence, not absence

The permit has exactly transaction_id, permit_id, native_binding_sha256,
intent_sha256, source_sha256, output_sha256, analysis_evidence_sha256,
checkpoint_reference, authority_ref, evidence_refs and outcome. Outcome must be
CONFIRMED_PRE_DISPATCH. Bind transaction_id to the original gate run_id, the exact
native binding, original retained intent and full source/output/evidence digests.
References identify the original checkpoint/version, exact code/policy review,
owner's operation authorization and positively reviewed non-dispatch evidence.

The host must authenticate those references, their scope and actual source/target
read evidence. verify_authority(permit) freshly returns that exact permit only
when all these facts are established; otherwise it rejects. An echo callback or
text label is not authority. An empty destination is necessary to continue a
create, but never proves non-dispatch. Provider failure/timeout, missing response,
unknown started effect, partial logs and journal loss do not qualify. Historical
Tengri evidence needs an explicit review accepting the complete host trace and
its pre-provider failure boundary; no provider-native audit log was exposed.

## API and retained evidence

Call recover_checkpoint_supervised with the unchanged context and exact native
supervised_kwargs, original_intent, permit, read_checkpoint, read_recovery,
append_recovery, verify_authority and verify_assignment. The original context
(including old source/code/policy evidence) stays frozen. authority_ref separately
pins the approved recovery implementation/policy and operation. No live permit
is supplied by this implementation or by a test fixture.

- read_checkpoint(transaction_id) freshly reads the exact ORIGINAL retained INTENT;
  there is no original-intent writer in this recovery API.
- read_recovery(transaction_id) returns the fresh complete ordered recovery event
  list. An empty list means confirmed absence, not failed access or a new key.
- append_recovery(transaction_id,event) retains an event without replacing earlier
  records or unrelated checkpoint content; unknown results never retry blindly.
- verify_assignment freshly verifies the current exclusive OWNER_INVOKED_SUPERVISED
  assignment for the same transaction/assignment/actor. Schedules do not qualify.
- request supplies authenticated original-source revision/complete bytes and exact
  target account/parent/dependencies/grants. Existing host obligations remain.

Remote intent comparison/digests use canonical JSON so a declared tuple can cross
JSON as an array. The native full analysis gate still requires required_domains
as a tuple. This is typed transport handling, not weakened source/output matching.
The host must normalize its native gate at that declared boundary.

## One-shot ordering and recovery

1. Validate the entire frozen binding/gate/intent/permit before effects. Refuse a
   missing/symlink journal; no reconstruction or bootstrap. Hold the same companion
   checkpoint lock and native journal lock as ordinary processing.
2. Freshly verify original intent, owner authority/assignment, native INTENT and
   destination absence. Require no previous recovery history. Retain AUTHORIZED
   and independently read it back before entering native execution.
3. After native source/output/source checks, insert one recovery_attempt row in
   the ORIGINAL SQLite journal and commit with synchronous=FULL. It records the
   exact permit. Never change INTENT to PREPARED or edit the original binding.
   The singleton is per transaction, not permit ID: a new permit cannot retry it.
4. Before the provider boundary retain DISPATCH_STARTED, independently read it,
   recheck source, destination, intent and assignment, then dispatch at most once.
   Lost/failed retention consumes the continuation and holds; no provider effect
   is inferred. A stale worker is not remotely fenced; only one cooperating host
   is supported, with independently established exclusive assignment.
5. On exact native output/source readback, retain a separate RECEIPT event and
   independently read it. Reconcile native output/source again read-only before
   reporting RECOVERY_RECEIPT_READBACK_MATCHED. Original retained INTENT remains
   unchanged; the native state may advance INTENT -> VERIFIED normally.

Use reconcile_only=True with allow_create=False after a consumed recovery. It
requires matching native permit consumption and exact retained AUTHORIZED /
DISPATCH_STARTED history (plus a receipt if already saved). It cannot dispatch.
A matching provider effect can yield a retained/readback receipt without another
create; absent output remains held. A lost receipt reply is reconciled by fresh
reads, not another append. Missing or conflicting evidence stays held.

## Tengri live evidence and approval boundary

The real transaction remains NEXUS-TENGRI-OWNER-20261126-01. Its journal is preserved
under /workspace/tengri-live/execution.sqlite, INTENT/module_id=null, observed hash
bf83cf0856ec226bc57f3586110e15a1716356180f9d3f33951832810800c285. Binding hash
8813b71d7c05f45d5f741495b0cb9a58cc5727994752c248f4af92bea6cf9724; analysis fingerprint
9c6079d6a0c575d4a78b61d195f0af5b95c221f3c8e23109df4ccdca8b5851e6. No private transcript,
intent body or journal is published here. These hashes identify observations,
not approval or provider attestation. Destination absence was freshly confirmed.

Host trace records1–15 cover failed initial assignment, then source checks, intent
save/read and read-only reconciliation. No cortex_create request reached the
provider dispatcher; native create_requests=1 counted the guarded callback entry.
The JSON tuple/list mismatch explains the pre-dispatch barrier failure. These are
agent/host records, not independent provider logs or universal proof of absence.
A reviewer must explicitly accept their completeness for a concrete live permit.

After review approval: verify exact candidate code, original transaction artifacts,
current destination/source/grants and exclusive assignment, prepare the actual
permit with accepted evidence references, then use the SAME journal/transaction.
Do not run this candidate or mint a live permit during preparation. No new source,
output duplicate, transaction ID, schedule or unattended acceptance is authorized.

Validation uses synthetic callbacks/journals, including one-shot consumption,
unknown committed/absent outcomes, lost event/receipt replies, wrong bindings,
missing journals and duplicate targets. It is not a live provider recovery.
Rollback removes the optional wrapper/native arguments, tests, document and rule12;
preserve real recovery rows/events and reconcile any consumed operation read-only.
Never delete recovery history to regain permission to create.
