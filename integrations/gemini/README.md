# Gemini connection pilot

**Secret migration candidate:** follow [secret-boundary.md](secret-boundary.md)
before using this revision. It uses the `gemini-pilot` environment and its
`GEMINI_PILOT_API_KEY` secret. The repository-secret setup below describes the
historical pilot and is superseded by that migration guide.

Status: the fixed library task passed live run 40121331969. Custom task input is a new candidate, not live-verified. This remains an indirect GitHub bridge, not a direct ChatGPT connector.
The existing isolated audit workflow is unchanged. This separate workflow has network
access and receives one secret only for its API step. It does not run the audit container.

## Phone setup

After this PR is reviewed and merged:

1. In Google AI Studio, use an API key belonging to your **Free Tier** project.
   Do not use either Tier 1 project, enable billing, or paste the key into a chat.
2. In this repository open Settings → Secrets and variables → Actions →
   New repository secret. Name it `GEMINI_API_KEY`, paste the key as the secret value,
   and save. Do not put it in a variable, commit, issue, or PR.
3. Open Actions → Gemini synthetic connection test → Run workflow. Select `main`,
   confirm the key belongs to the Free Tier project, and run once.
4. Return the run URL to the coordinator. The coordinator can retrieve job logs
   and inspect the escaped `NEXUS_GEMINI_RESULT` line through the GitHub connector.
   A passing workflow alone does not establish that the answer is correct.

This connector cannot set GitHub secrets or dispatch Actions. The owner performs
those two steps in the phone browser. No claim of an automatic conversational
Gemini tool or always-on orchestration is made.

## Bounds

Blank task input uses the fixed fictional library scheduling question. Custom input is limited to synthetic packets and requires a separate owner confirmation. No private Nexus content is authorized. The public repository's workflow logs may be public. Gemini's free
tier may use submitted content to improve products. No Notion or Cortex credentials
are available to this job, and no writes to those services are attempted.

The model is fixed to `gemini-3.5-flash-lite`, with one request, 512 maximum output
tokens, 45-second transport timeout, 64 KiB response cap, no tools, redirects, retry,
model fallback, or unstructured prompt input. An uncertain transport result stops;
it does not prove the provider did not process the request. A fresh manual run is
a new request. The concurrency group serializes runs but does not deduplicate them.

Free Tier confirmation is an owner assertion, not an API billing guard. An API key
does not expose its billing tier to this script. If a paid-project key is supplied,
the request can incur a charge. Never enable billing for this pilot. Quota errors
stop the test; they do not trigger a paid upgrade.

A repository secret can be referenced by other trusted repository workflows.
GitHub secret masking is an additional safeguard, not proof against hostile code.
Review future workflow changes and delete the secret to disable the pilot.
The workflow itself only permits manual runs on main; it has no push, PR, schedule,
or external event trigger. It uses no third-party Actions or package installs.

## Offline checks

`python3 -m unittest discover -s integrations/gemini -p 'test_*.py' -v`

These tests mock transport: no API key or real Gemini call is needed. They cover
preflight refusal, fixed request bounds, one-call behavior, secret/body suppression,
provider failure, malformed/truncated/tool responses, body limits, and redirects.
They do not verify live credentials, tier, quota, model availability, or answer quality.

## Official references checked 2026-10-24

- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/api/generate-content
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets

The fixed-task live success establishes API reachability for that key/model at that time. It does not close restricted identity or the wider foundation audit.


## Custom synthetic packet candidate

In the manual run form, `task_json` may contain the contents of `example-task.json`.
Check both the Free Tier confirmation and the separate synthetic/nonprivate/public-log
confirmation. Blank input preserves the original library test; custom input without
confirmation fails before transport. Do not rerun an old job to select new inputs.

Schema: exactly `task_id`, `classification`, `question`, and `sources`. Task IDs must
start with `synthetic:` and contain only lowercase letters, digits, colons and dashes.
Classification must be `synthetic`. Supply one to five sources, each containing only
an ID (`S1` through `S99`, unique) and nonempty text. Question and each source text
are at most 2,000 characters; the complete input is at most 8,192 UTF-8 bytes.
Duplicate JSON fields and unsupported fields are refused.

The owner classification is not an automatic privacy detector. This public-repository
pilot must not receive real personal, canonical Nexus, credential or confidential
content. Exact matches of the configured key in the assembled prompt are refused;
this is not comprehensive secret detection. Inputs flow through environment variables,
never shell interpolation or execution. No model tools or browsing are enabled.

The result includes the task ID, canonical packet SHA-256, and full prompt SHA-256.
The historical `source_sha256` field hashes the full prompt, not each source separately.
The canonical packet hash is null for the original fixed task. New packets include all
source IDs and text in their canonical hash. Reusing an ID does not deduplicate requests.
The output remains PROPOSED and must be reviewed here before any further action.
Source citations and distinction between inference and evidence are model instructions,
not a mechanical guarantee; the coordinator checks the answer against supplied sources.

Example acceptance rubric (not an independent benchmark): 12 kits require 24 pencils;
the sheet lists only 20, a shortage of four. Notebooks suffice on paper. Physical stock
is unverified and kits are unassembled, so complete readiness cannot be confirmed.
No live call using this packet has been made. Thirteen offline tests currently pass.
