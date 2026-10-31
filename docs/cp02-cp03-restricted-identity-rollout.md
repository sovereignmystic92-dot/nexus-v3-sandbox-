# CP02 / CP03 restricted executor identity rollout

Status: **DESIGN AND TEST PLAN ONLY**. No credentials, identities, permissions, provider settings, workflow triggers or production integrations have been changed.

The policy in `tools/restricted_execution_identities.json` specifies intended *separate* identities for the human owner, offline CI, Notion read, Notion bounded append, Cortex analysis, GitHub maintenance, Gemini independent review and browser public research. It is a proposed authorization model, **not an enforced runtime control**.

## Why this is necessary

- The current owner-connected Cortex module exposes view, edit, admin, delete and transfer permissions. Those grants belong to the authenticated caller; a restricted analyst must have its **own provider identity**, not simply an application-level role label.
- The connected Notion workspace authenticates, but the current tools do not establish a separate restricted provider principal.
- GitHub Actions protected environments are distinct from ChatGPT connector sessions, Automations, Codex, Browser Use and Google Cloud Shell. Their credentials must not be assumed shared or isolated without evidence.
- Synthetic CI is deliberately credential-free. Do not give it an owner token merely to test denied access.

## Bounded rollout and proof gates

1. **Identity discovery**: for each provider, obtain the authoritative identity/principal and effective grant inventory, without collecting token values. Mark unobservable scopes UNKNOWN, never PASS.
2. **Provision only if supported**: create separate least-privilege provider identities for each required capability, using provider-supported permission boundaries. Owner explicitly approves any provider-level permission/identity change before execution; do not revoke the owner's recovery access.
3. **Binding proof**: show which runtime/workflow can receive which restricted credential and destination, including Automations, Codex, cloud browser and Cloud Shell where used. Bind one identity per purpose and avoid secret forwarding.
4. **Negative proof**: from each restricted identity, safely attempt only an unauthorized **read of a harmless owner-designated synthetic fixture**, expecting provider-side denial; never test against real private pages or leak token values. Record principal, fixture, action, result and immutable run reference.
5. **Positive proof**: from that same identity, demonstrate the minimum allowed action on a designated synthetic fixture; independently read back the effect where applicable. Never promote on simulated policy decisions alone.
6. **Independent review**: Gemini or another reviewer receives a source/evidence packet and returns an independently authored assessment. Reviewer cannot change its own test evidence.
7. **Closure**: CP02 requires provider-side effective grant and denied-access evidence; CP03 requires credential/mount exclusion across all in-scope execution hosts. Keep both open until independently accepted.

## Risk controls

- Owner retains emergency recovery and approvals; restricted identities do not inherit module administration, deletion or ownership transfer.
- Notion remains canonical transcript/source archive. Cortex remains analysis/context; no silent authority transfer.
- Default is deny, and unattended jobs never use owner credentials.
- Self-review permitted in existing GitHub environments is a documented independence weakness, not silently accepted as an independent reviewer.
- Do not turn on new triggers, change environment secrets, create billable resources, or weaken branch protection for this rollout.
- Existing CI routing checks are source controls; this policy file alone cannot prevent a privileged connector tool from performing a write.

## Next external dependency

Confirm provider-supported restricted identity options and actual effective grants for Notion, Cortex, GitHub App and any Automations/browser/Cloud Shell hosts used by Nexus. Only then request narrowly scoped approval for concrete provider-side changes. The current evidence supports **13/19**, not checkpoint closure.
