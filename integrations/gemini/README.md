# Gemini connection pilot

Status: prepared synthetic pilot; not a direct ChatGPT connector, not live-verified.
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

The only input is a fixed fictional library scheduling question. No private Nexus
content is sent. The public repository's workflow logs may be public. Gemini's free
tier may use submitted content to improve products. No Notion or Cortex credentials
are available to this job, and no writes to those services are attempted.

The model is fixed to `gemini-3.5-flash-lite`, with one request, 512 maximum output
tokens, 45-second transport timeout, 64 KiB response cap, no tools, redirects, retry,
model fallback, or arbitrary prompt input. An uncertain transport result stops;
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

The first successful live result will establish API reachability for this key/model
at that time. It will not close restricted identity or the wider foundation audit.
