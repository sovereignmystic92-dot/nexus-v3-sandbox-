# Ordinary Notion records and private journal custody — draft

## Read interface implemented

NotionRecordReader adapts an injected connected-fetch callback to the shared
record verifier. It accepts decoded page exports, binds returned page ID to the
requested ID, extracts exactly one direct parent from the ancestry envelope, and
rejects ambiguous content wrappers, unknown/truncated exports and missing or
repeated raw-section headings. Source-like parent tags in the body cannot
substitute for actual ancestry. Unsupported layouts hold.

The supported payload view is either the entire rendered content or one exact
heading through the end. Whitespace is preserved. This is a narrow export parser,
not a full Notion API/block parser. Rendered markup can differ from original text;
an independently obtained expected hash must still match. Missing truncation
metadata is not provider attestation that the full service export is complete.
Exact selected-payload preservation does not establish external truth, complete
duplicate enumeration, full-page semantic coverage or source-video fidelity.

Validation: 27 focused local tests passed (9 reader, 10 journal, 8 verifier). The
reader also consumed a fresh host-fetched existing real transcript and matched all
16,386 originally supplied characters. No private transcript, IDs, fetched exports
or journals are included in this public change. The callback in this exercise
read the host's captured fetch document; it is not an autonomous authenticated
network client. No provider writes occurred.

## Storage deployment decision

The required deployment shape is one trusted worker with a private persistent
filesystem volume holding SQLite and its sidecar files. The volume must be outside
the public checkout, outside temporary scratch, excluded from logs/artifacts and
backed up privately. No specific mounted volume or provider is verified in this
session; provisioning remains NOT DONE. This document does not create storage.

Before a live write, record the actual execution host, persistent mount identity,
absolute journal path, worker identity, expected journal identity and the source
of that expectation. Confirm owner-only access and that no real content enters
public CI. Initialize once; subsequent runs must reopen using the same identity.
Never reset identity or initialize a replacement after loss just to continue.

Verify custody by creating a harmless journal operation, terminating and
restarting the actual runtime, reopening the same journal, confirming intent and
remote-ID binding and checking a repeat remains reconcile-only. Test an explicit
private backup/restore, then independently read back the relevant provider record.
A runtime restart test does not prove total-host-loss recovery; keep those claims
separate. Missing/corrupt journal or failed custody verification blocks mutations.

SQLite synchronous commits and mode 0600 help local integrity; they do not provide
volume encryption, independent backups, remote fencing, multi-worker safety or
survival of host loss. Remote provider access remains mediated by separately
authorized connectors. No credentials are loaded by this code.

## Remaining real-write integration

The caller still must supply: complete scoped lookup including pagination;
metadata/title and source/output bindings; authorization for the precise target;
trusted journal custody; and an executor that commits intent before any external
create, reconciles uncertain outcomes, and enforces verification before completion.
The existing synthetic adapter remains unchanged. No complete Notion mutation
transport, automatic bootstrap, durable deployed runtime or production activation
is introduced. Adoption requires review of the exact final changes and evidence.
