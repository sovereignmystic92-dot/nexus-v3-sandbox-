# Nexus Codex task intake

This workflow provides a bounded, manually dispatched engineering-task intake. It **does not execute Codex**. It validates an existing open GitHub issue, checks for an owner-controlled `nexus:codex-approved` label and required headings, then publishes a JSON artifact with `INTAKE_VALIDATED_ONLY`. Missing requirements fail closed.

## Issue template
Use these headings in the issue body:
- `## Goal`
- `## Scope`
- `## Acceptance criteria`
- `## Safety boundaries`

An owner with issue-label permission must explicitly add `nexus:codex-approved` after reviewing the scope. Then manually run **Nexus Codex task intake** with the issue number. No issue comments, commits, or provider writes are performed by this workflow.

## Execution adapter still needed
To actually execute Codex, separately integrate a documented and authorized Codex runner or cloud task mechanism. Require owner-approved mission scope, bounded repository permissions, trusted event provenance, and auditable result links. Never treat issue intake or a successful synthetic test as evidence that Codex ran. Avoid running untrusted issue content as shell commands. Do not create a token or guess an API endpoint.
