# Proposal: ordinary supervised transcript custody without a versioned file port

Status: PROPOSED / NON-GOVERNING. No permission, implementation activation or live
transaction follows from this document. Base: merged PR357,
76e1be2500fbf673781704461581a5d85230c143. Owner requested the smallest explicit
simplification if compatible existing private storage is unavailable.

## Observed capability boundary

- Existing source/analysis tools: authenticated Notion and Socra Cortex.
- Existing CLI: mandatory-gated execute_supervised and its opt-in custodied CLI.
- No create_library_file / prepare_materialize / replace_library_file tools.
- Basic Memory bm_write declares expected_checksum conditional replacement, but
  project discovery returns only getting-started/main, both is_private=false.
  No approved private Nexus journal target or immutable binary retention was
  established. No note or project created; checksum semantics were not live-tested.
- Pages edit_page declares hash-guarded single-block replacement; file upload
  returns a persistent digest-bearing reference. Neither alone establishes the
  pinned protected journal head, immutable retention or versioned file contract.
  A scoped Nexus-custody search returned no target, not global absence. No writes.
- /workspace is overlayfs. Prior checkout survived this invocation, proving
  observed continuity only, not durable storage across host replacement. Local
  flock/SQLite can serialize cooperating workers; neither is remote fencing.
- Environment status reports no configured runtime variables/secrets or outbound
  identities. No existing private file service binding is evidenced by that result.

Do not map unconditional Cortex/Notion updates or filesystem rename to the current
VersionedCustodyDispatcher store_replace contract. No compatibility probe wrote
private source material to an unverified destination.

## Exact proposed policy exception (requires owner/repository review)

For ordinary owner-invoked, single-writer source processing only, permit the
existing native execute_supervised path with a local FULL-synchronous journal,
provided that the trusted coordinator also retains and independently reads an
exact, self-contained pre-effect intent in the existing authorized Cortex
operational checkpoint before dispatching the one provider effect. Do not require
an additional versioned binary-file service solely for this bounded mode.

Keep the analysis_gate, exact complete source/revision binding, target/grants,
duplicate reconciliation, source/output/source readback and actual execution
receipt. Do not relax existing-output append authorization/exclusive custody.
Unattended or parallel execution, remote takeover and full host-loss acceptance
remain outside this exception. This is not a blanket alternative to custody.

The retained intent must bind the stable transaction/enrichment ID; exact source
page, revision, UTF-8 digest and fidelity receipt; runtime/policy revision; target
name/ID/parent/owner and dependency baseline; complete desired output and digest;
complete analysis evidence and fingerprint; operation kind; authoritative local
journal path; and state. Original text stays in Notion: do not duplicate its full
chunks merely to keep an intent. The output/evidence binding is sufficient to
reconcile the exact effect; reconstructing a native source/journal from lost text
is not automatic recovery authority.

A single coordinator must reserve this exact task for the invoked session and
must not overlap with another writer. Two matching checkpoint reads are evidence
of observation, NOT proof of mutual exclusion or CAS. If exclusive assignment
cannot actually be established, or a checkpoint changes, stop and reconcile.
Do not invent lease enforcement from an owner label or caller flag.

Before provider mutation: native committed INTENT -> exact checkpoint intent
saved -> independent readback -> source/destination recheck -> one effect.
After mutation: native guarded output readback -> retain actual receipt and native
journal state/identity -> independently read saved receipt -> report the precise
completed scope. Unknown checkpoint/provider outcomes stop; inspect before retry.
No post-effect metadata may retroactively claim pre-effect intent.

On lost local journal, preserve the retained binding and HOLD the transaction.
Exact provider reads may establish the matching effect for operator reconciliation;
absence never authorizes recreation. Do not reset intent, choose a new ID or
synthesize a VERIFIED journal. A later reviewed recovery path may adopt the
self-contained intent; no such path is installed by this proposal.

## Smallest implementation follow-through after policy approval

Use the existing host request callback to add a pre-effect operational-checkpoint
intent/readback barrier, plus the post-result receipt/readback barrier. Keep the
native journal and all current mandatory evidence checks. Do not introduce a new
CLI, provider, store, credentials, scheduler or runner. The current binary-custody
path remains available for workloads that require its stronger restoration scope.

Make the intent-before-effect barrier enforceable in the callback rather than
relying on prompt text. Bind returned checkpoint identity/version/digest as
observations without claiming provider CAS. Exercise failure before intent save,
lost intent acknowledgment, mismatching readback, uncertain provider effect and
lost local journal with the existing test infrastructure. These are proposed
acceptance cases, not executed or passing tests.

Do not enable a live call until exact destination grants, authoritative task
assignment, checkpoint retention scope and these callback semantics are reviewed.
This proposal preserves durability of the remote intent/receipt while explicitly
holding, rather than promising automatic recovery after loss of the native journal.

## Tengri disposition and review decision

First real candidate remains youtube:e-Hc1Bp-piE, original
4078c067daa48105b81dc86ebf8e9647, existing Notion analysis
4078c067daa48126b4f8c68ed20eec51 and existing connection
3c88c067daa48199a131f1a8146d5b15. No new original, output or connection is created.
Reconcile current Cortex records and retained transactions before selecting create
or the supported append path. Do not replace the existing historical analysis
with a new source ingestion merely because a Cortex keyword search is empty.

Review decision requested: approve/reject this narrowly bounded exception and its
explicit lost-journal HOLD behavior, or provide an existing compatible private
versioned file target with authoritative custody mapping. Until then the live
transaction remains blocked; merged CLI code is not execution evidence.

Validation of this change is documentation-only: verify links, scope and unchanged
runtime/AGENTS/policy files. No synthetic acceptance or factual research success
is inferred. Rollback removes this proposal and its navigation link; preserve any
prior real intents/receipts. No active policy text is amended.
