# CP03 cross-service access readback and closure decision — 2026-10-31

**Decision: CP03 remains PARTIALLY_VERIFIED. Foundation Audit remains 13/19.**

## Evidence acquired without credential values

- GitHub Actions run 41205263008, job 124548930456: a no-environment host process confirmed absence of seven fixed credential variable names. This does not prove absence from files, other processes or hosts.
- GitHub owner screenshots: notion-sandbox and gemini-pilot have main-only deployment branches and required owner review. Self-review is allowed; administrator bypass disabled. Names of environment secrets were truncated in screenshots.
- GitHub App installation 174264654: repository selection is selected, not all. No authoritative full OAuth/App permission matrix was returned.
- Connected Notion readback: authenticated workspace and user identity were returned by the connection. The tool access query confirmed search is available. This proves connection access, not workspace-wide grant restriction, storage isolation or GitHub Actions secret boundaries. Personal identity and email are deliberately omitted from this public record.
- Connected Socra Cortex readback: a Nexus transcript routing module returned module.view, module.edit, module.admin, issue.view, issue.create, issue.comment, issue.edit, issue.admin, module.delete and module.transfer; the current caller is the owner of that module. These are broad **module-specific effective permissions**, not evidence of unauthorized access. Do not infer that a GitHub job can use these permissions.
- ChatGPT Automations, Browser Use, Codex and Gemini CLI/Cloud Shell are distinct execution surfaces. Their complete effective grants and credential storage/isolation have not been independently inventoried.

## Accepted evidence versus missing proof

**Verified:** source-level credential routing is guarded by CI; seven negative/positive synthetic tests passed; one no-environment GitHub host process excluded seven fixed protected variable names; provider workflow environments are configured with main-only and owner approval; Notion connection identity and Cortex module-specific access can be read.

**Not verified:** all secret-bearing filesystem/mount and host paths; negative runtime access across every provider and connector; independent assurance of Notion/Cortex/Automations/Codex/browser credential isolation; GitHub App full effective grant matrix; independent assessment of the GitHub runner host boundary (CP01).

**Security observation:** Cortex grants include module administration, deletion and ownership transfer. This may be appropriate for the owner's authenticated session; it must not be represented as least-privilege for a restricted synthetic test identity. Changing permissions requires a separate owner-approved scope decision and must not be done merely to inflate audit counts.

## Disposition

Do not promote CP03 to PASSED until a complete in-scope credential/mount inventory and independently attributable denied-access tests establish exclusion from unauthorized execution surfaces. Do not split or narrow the checkpoint to count only GitHub Actions. CP01 remains PARTIALLY_VERIFIED. No secret values, production writes, permission changes or additional costs occurred in this read-only cross-service assessment.
