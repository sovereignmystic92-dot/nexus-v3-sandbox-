# Network, triggers, recovery, readback and cleanup — bounded follow-through

Reviewed base: `d5f9a1e98052bc23933d1999b73b70aeb0c1522e` (2026-10-24).
Thirty code/data blobs used for local work matched this repository revision.
This report consolidates the four requested areas and records concrete changes;
it does not close full foundation acceptance or change the fixed 8/19 tracker.

## Network and triggers (C4)

The synthetic acceptance job fetches public source and a pinned image on its host,
then executes tests in a network-none Docker container. Gemini live analysis runs
on a separate network-enabled host, manually dispatched on main with confirmations
and an environment reference. The offline Gemini job has no environment or secrets;
its tests execute with network none. No whole-repository network-isolation claim
is justified by the audit container's settings.

This candidate adds actual UDP/IPv4 and TCP/IPv6 denial probes to the audit container
alongside its existing TCP/IPv4 probe. These are bounded documentation-address probes,
attempted only after loopback-only and no-default-IPv4-route preflight. Unsupported
IPv6 is accepted as unavailable, not proof of an IPv6 firewall. Timeouts do not prove
denial. Credential-name screening now includes API_KEY and PRIVATE_KEY names.
No credential values are printed. Name screening is not exhaustive secret detection.

A new exact workflow-byte inventory is checked automatically in the offline CI job.
It rejects added, removed, symlinked or changed workflow files until the committed
review policy is explicitly updated. Thus a newly added schedule/trigger or changed
network/secret declaration cannot pass unnoticed by this check at the same policy
revision. It is not semantic YAML validation, immutable authority, a server-side
required check, or a defense against jointly malicious policy/workflow changes.
Trusted review is still necessary. Repository hooks, external schedulers, organization
settings and host-wide outbound controls remain outside this inventory.

## Recovery and fresh readback (C6/C7)

Three new process tests cover exact restoration followed by a fresh Python process
reading the retained installation/inventory; deliberate post-restore identity mutation
rejected by another fresh process without repairing bytes; and killed restore staging
followed by explicit cleanup, restoration and fresh readback. The fresh process has
no inherited in-memory adapter state but shares the same filesystem, kernel and
operator-supplied trusted inventory. This is process-independent verification, not
an independent principal, provider or physical fault domain.

Existing paired-checkpoint checks continue to require both designated copies and a
caller-trusted latest witness. Both copies agreeing is insufficient to authenticate
that witness. Protected latest-checkpoint authority, loss of all local trusted state,
remote history/currentness, real storage-service reconciliation and adversarial
replacement of all witnesses remain open. No live Notion or Cortex writes occur.

## Interrupted cleanup (C8)

The new test pauses a child inside the real paired-restore path after checkpoint bytes
are staged and before destination publication. The parent sends SIGKILL, verifies the
journal remains absent and committed inventory unchanged, then invokes the existing
validated staging cleanup. It confirms one abandoned directory is removed and a later
restore succeeds. It is an actual child-process interruption, not a simulated exception.

This does not kill the GitHub runner/host, prove platform workspace erasure, test every
publication crash point, establish storage retention/deletion, or make cleanup safe
against concurrent hostile filesystem mutation. Single stopped-worker requirements
remain. Existing cleanup preflights and evidence-preservation holds remain unchanged.

## Execution and acceptance

Local: `python3 tools/validate.py --output local-evidence.json` passed **162 distinct
tests** (153 baseline plus nine additions). New tests: four network preflight tests,
three process recovery/readback/cleanup tests and two workflow policy tests. The
workflow inventory also matched locally. Docker is unavailable in the authoring
workspace, so actual network-none probes require the hosted PR run.

Hosted PR evidence is pending at initial publication. The acceptance runner separately
executes four existing coordinator fault cases; they must not be counted as new restore
crash cases. The separate 13 Gemini mocked tests do not increase the 162-test count.
No real Gemini API call is part of these checks.

The Gemini environment was observed holding run 40129426274 with no job steps, and a
duplicate was cancelled. Completion after owner environment approval remains unverified
in this record. Earlier migration run 40129142342 succeeded before that hold was tested.
Owner reports repository-secret deletion; complete secret/settings inventory is unavailable
through the current connector. Restricted Cortex identity and C9 fencing remain deferred;
independent human review remains outstanding.

Next acceptance work requires evidence that these local/hosted checks cannot supply:
protected latest-checkpoint witness storage, a real host-stop lifecycle boundary,
server-side environment branch-denial testing, and complete settings/hooks inventory.
