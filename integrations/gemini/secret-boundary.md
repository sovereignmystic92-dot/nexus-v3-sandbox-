# Gemini pilot secret migration

Status: proposed configuration change. Environment policy and secret migration have
not been executed or independently verified. No API key was read or exported.

## Boundary

Use a GitHub environment named `gemini-pilot`. Put the Free Tier project's key
there as `GEMINI_PILOT_API_KEY`. The workflow passes it to the Python script as
`GEMINI_API_KEY`; the Python API contract is unchanged. The renamed secret avoids
silently falling back to the existing repository secret named `GEMINI_API_KEY`.
Do not create the new name as a repository or organization secret.

Environment secrets are not a per-workflow access-control list. Other workflows
can reference the same environment. Branch restrictions and review gates control
access to its jobs. A trusted reviewer must inspect workflow code and the exact
run revision before releasing credentials. This does not remove repository-admin
authority, prevent every malicious workflow, or enforce a network egress allowlist.

## Owner phone setup, before merging

1. Open repository Settings → Environments → New environment, name `gemini-pilot`.
2. Under deployment branches/tags select selected branches/tags and add a **branch**
   rule matching exactly `main`. Do not add tag access or broad wildcards.
3. Enable required reviewers and select `sovereignmystic92-dot`. Keep prevention
   of self-review off so the sole owner can approve a manually started run. This
   adds an owner approval gate, not independent human review. Disable administrator
   bypass if the interface offers that setting. Save the protection rules.
4. Add an **environment secret** named `GEMINI_PILOT_API_KEY`, using the Free Tier
   project's key through GitHub's secret field. Do not paste it into chat or a file.
   GitHub cannot reveal the old repository secret. Retrieve the key from your own
   secure copy or the provider interface; do not send it to the coordinator.
5. Delete the old repository-level `GEMINI_API_KEY` after the environment secret and
   policy are configured. Leaving the old copy keeps the previous broader access.
   Check secret names only; never screenshot values. The old workflow cannot run
   successfully after this deletion until the candidate is merged; that pause is
   intentional. Do not restore a repository-level fallback to work around failure.

Creating an environment without setting its rules does not protect it. GitHub may
auto-create a missing environment when a workflow references it; this is not proof
the policy or secret exists. Missing credentials make this script stop before an
API request, but the YAML itself cannot attest environment-policy configuration.

## Validation after owner configuration and merge

- Record environment name, allowed branch rule, reviewer, bypass setting and secret
  name without any values. Read current settings if the available interface permits;
  owner screenshots are owner-supplied evidence, not independent API verification.
- Confirm the old repository secret name is absent. Organization-level secret access
  is a separate inventory limitation if not inspected.
- Start one new fixed synthetic test on main with Free Tier confirmed. Verify that
  it waits for owner environment approval, then approve only this reviewed revision.
- Retrieve its result and check the supplied task, source binding and proposed answer.
  A successful API call alone does not prove that approval or branch policy enforced.
- A denied non-main environment attempt remains a distinct future negative test;
  the existing job-level main guard skips before reaching the environment policy,
  so that skip cannot prove server-side environment rejection.

No scheduled runs, Notion/Cortex credentials, app writes, permission expansion,
paid upgrade or independent-review acceptance are included. C3/C4 remain open.

References checked 2026-10-24:
https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments
https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
