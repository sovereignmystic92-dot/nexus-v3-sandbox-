# Sandbox recovery workflow v2

Status: adopted operating specification after merge; implementation and recovery acceptance remain incomplete. Standing owner approval covers verified sandbox fixes and merges. Ask before costs; platform controls still apply. Production operations remain paused.

## Roles and order

Codex freezes a synthetic checkpoint for an exact source commit. GitHub runs the checks and retains code/evidence history. Notion and Cortex store identical recovery packets in explicitly bound test destinations. Codex separately reads both and compares identities, destinations and packet hashes. Only then may a reviewed manifest and latest accepted reference be merged. Fresh GitHub/provider readback confirms adoption. Recovery is separately tested in a fresh process.

Each manifest identifies workflow version, installation ID, checkpoint sequence, UTC creation time, source commit, packet SHA-256, previous accepted manifest SHA-256, provider record IDs, and test/readback evidence. Workflow sequence is distinct from local event sequence and provider versions. Canonical hashes use sorted compact UTF-8 JSON with no NaN. Dates never resolve identity/hash conflicts.

The proposed latest reference belongs in GitHub main and pins the accepted manifest identity/hash. It is NOT initialized by this specification. A chain verifier must enforce sequence continuity and previous-hash agreement before automatic acceptance. A forward git commit can otherwise point to stale recovery data.

GitHub ruleset 25721028 was observed active on the default branch with PR, strict synthetic check, deletion and non-fast-forward restrictions, no bypass actors, and zero required approving reviews. Owner authorization is operational policy, not enforced independent review. Branch-protection endpoint returned 403. These observations are not a denial test or complete authority assurance.

## Implemented local-loss extension

restore_lost_local_state explicitly reconstructs absent journal/inventory only after supplied paired copies match a caller-authenticated CURRENT witness, bounded decoding and SQLite integrity pass, and inventory path, installation, event sequence, catalog and identity anchors match exactly. Existing/conflicting state is preserved. No startup fallback or remote write is added.

184 local tests pass, including ten loss-recovery cases. They delete the whole declared local directory after committing a verified synthetic request. A fresh process reconciles the recovered request without another remote write. Coherent stale/rewritten copies, corruption, missing witness, wrong path and conflicting retained state hold. Interrupted inventory publication can resume with exact evidence.

The tests supply packet copies and witness as offline fixtures. They do not establish protected current external authority, live Notion/Cortex custody or physical host loss. The existing paired packet v1 is unchanged; workflow v2 describes the surrounding process, not a journal migration.

## Open requirements

Protected latest-reference semantics, currentness after local loss, live paired recovery, scoped provider permissions, retention/history and wider physical fault domains remain unproven. CP06 stays PARTIALLY_VERIFIED; accepted count remains 10/19. Notion/Cortex sandbox use is authorized; no Gemini activation, production promotion or unattended scheduler follows.
