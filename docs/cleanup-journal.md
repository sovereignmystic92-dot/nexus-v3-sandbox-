# Cleanup checkpoint and reprocessing handoff

This change adds a durable, inspectable handoff to the CP08 abrupt-runner cleanup
probe. It does not change CP09, install a background recovery worker, or change
checkpoint scores. Ordinary runner cleanup is unchanged; this first integration
covers the exact owned resources discovered by the surviving-supervisor probe.

## Saved state

Before the deliberately induced runner stop, the probe creates an exclusive SQLite
journal outside the disposable namespace. It records run identity, source revision,
immutable Docker container ID and name, exact staging/namespace paths and their
device/inode identities. Initial state is PENDING with next step REMOVE_CONTAINER.

Each removal has a committed INTENT before its callback and a VERIFIED observation
after successful absence checks. An exception records UNCERTAIN. Abrupt process
exit can leave INTENT, which is intentionally not treated as success or failure.
Snapshots identify sequence, last verified step, pending/uncertain status, and next
permitted step. Container removal precedes staging removal, then empty-only namespace
removal; COMPLETE retains the journal rather than deleting the recovery record.

The supervisor logs the saved checkpoint before stopping the runner and after each
step, with the journal path. A log emission is not proof of independent remote custody.
The SQLite journal is the process-restart checkpoint; logs provide an inspectable
handoff even if the final success report is never emitted.

## Reprocessing

On the same surviving host with the original trusted journal available:

```sh
python3 tools/cleanup_journal.py /absolute/custody/cleanup-ID.sqlite
python3 tools/cleanup_journal.py /absolute/custody/cleanup-ID.sqlite --advance
```

The first command inspects only. The second performs at most one step. Every resume
observes actual state first. Confirmed absence advances without repeating removal;
API errors are unknown, not absence. A present container must retain its immutable
ID, name and source mount. Directories must retain recorded identities and cannot
be symlinks. New or replaced resources are held rather than deleted. Unexpected
namespace contents prevent removal. Failed journal writes stop before the action.

No silent journal reset or reconstruction is supplied. Reopening a missing, corrupt
or mismatched journal fails. Preserving the journal is necessary: losing all journal
history or coherently rewriting it is outside the assurance. The journal is not an
authenticated external witness and callbacks operate under the host's trust boundary.

## Custody and limits

The hosted probe uses RUNNER_TEMP/nexus-cleanup-journals outside the disposable
resource tree. That survives probe/worker-process restart on that host, not loss or
replacement of the GitHub-hosted VM. GitHub workflow logs have their existing retention
policy; no artifact upload, new credential, provider integration or external storage
was provisioned. A new hosted runner must inspect retained logs and establish current
resource/host identity; it cannot assume the previous VM or local journal still exists.

Automatic cross-host reprocessing requires independent persistent checkpoint custody
and host/resource identity binding. That remains unimplemented. No claim is made that
every workflow stage or creation-before-discovery interruption is journaled. If the
probe fails before verified resource discovery, preserve the failure for inspection;
there is no authority to infer resource names or delete unrelated resources.

The probe no longer uses an unjournaled finally-block removal or automatic temporary
directory deletion to conceal an uncertain outcome. Failed cleanup can leave the
owned resources for explicit reconciliation; the hosted VM remains disposable.

The single-worker restriction remains. Filesystem identity checks are not atomic
protection against another actor replacing paths between checks and removal. This
change supplies an observable handoff, not CP09 fencing, total-host-loss recovery,
future retention expiry, provider erasure, or universal exactly-once execution.

## Validation

Targeted tests use temporary synthetic resources. They exercise fresh-process reads,
actual child-process exit after removal but before acknowledgment, lost replies,
unknown observations, identity replacement, symlinks, unexpected remaining files,
journal-custody exclusion, pre-action storage failure, and idempotent completion.
Hosted CI also runs the integrated real-Docker cleanup probe. Results and exact tested
revision are recorded in the PR; local mocked tests alone do not establish Docker behavior.
