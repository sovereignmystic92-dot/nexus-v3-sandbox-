# Nexus foundation audit sandbox — review draft

Target: `sovereignmystic92-dot/nexus-v3-sandbox-` (public).

Status: review draft based on AUD-40; not deployed or runtime-tested. This branch proposes files for review. It does not implement a working transaction coordinator.

The owner selected public visibility after the original private-repository blueprint. Only synthetic examples and generic design material belong here. Notion remains authoritative for Nexus; this repository cannot promote Nexus 3.0 or reactivate production operations.

## Included

- Architecture and component contracts.
- Sequential acceptance cases, with failure and concurrency cases separated.
- Evidence and preflight templates with unverified controls explicitly retained.
- Proposed SQLite schema and Python interface skeleton.
- Deterministic synthetic fixture.

No workflow YAML, service credentials, production page contents, external adapters, dependency installers or executable entry point are included. The absence of workflows does not prove that repository-wide Actions settings are disabled.

## Review sequence

1. Review the changes in the draft pull request.
2. Merge only after review; the branch preserves existing ignore rules and appends sandbox exclusions.
3. Implement the coordinator against the contracts.
4. Establish runtime isolation and execution scope before running acceptance cases.

Runtime identity, independent reviewer, retention, and host isolation remain unresolved. Google Cloud is a later hosting preference, not a provisioned resource or spend authorization.
