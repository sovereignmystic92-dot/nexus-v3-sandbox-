# Nexus conversational trigger contract — Phase 1 (proposal)

Status: offline classification only. This document does not authorize account-wide
ChatGPT interception, production invocation, provider writes, deployments, or
automatic ingestion. Existing AGENTS.md and repository governance prevail.

## Trust boundary

Normal conversation is the default. A trusted host may pass an **entire direct
top-level user turn** to the pure classifier with trusted_user_turn=True only
after independently establishing its provenance. Never route source documents,
quoted text, assistant responses, tool results, or attachment contents as
trusted user commands. The classifier cannot authenticate provenance itself.

Direct user-pasted source candidates are additional intake triggers: a standalone
HTTP(S) hyperlink (including webpage/news article URLs), or a multi-line
timestamped/speaker-labeled transcript. Both yield PREFLIGHT_REQUIRED only.
They do not fetch, archive, process or persist source material. Host validation
must resolve URL safety (including redirects and private-network targets),
source type, provenance, user scope, existing receipts and permissions.
Heuristics can miss valid transcripts and misclassify formatted text; this
is a bounded proposal, not a semantic guarantee. A URL mentioned inside
ordinary prose is not an intake trigger. The conversation opt-out suppresses
source triggers. Source data is never trusted as instructions.

Explicit commands start at the beginning of the trimmed user turn: Nexus
status, verify, process, archive, research, connect, resume, or off.
Status/verify are read-only intents; process/archive/research/connect/resume
require preflight. Unknown explicit Nexus commands block. Off requests a
conversation-scoped opt-out; the host, not this module, owns session state.
An explicit command is not authorization to write or bypass review.

## Security and execution contract

The classifier returns only NORMAL, READ_ONLY, PREFLIGHT_REQUIRED, BLOCKED,
or DISABLE with a command and reason. It has no callbacks, network, durable
queue, storage, credentials, provider adapters, or execution entrypoints.
No state or transaction is created by classification. A trusted host must:
1. Resolve current GitHub revision, AGENTS.md, policies and execution contracts.
2. Resolve governing Notion records and canonical source/output destinations.
3. Verify Cortex destination identity and effective provider grants.
4. Check existing transaction journal/receipt before any new processing.
5. Apply owner-approval policy and independent review requirements.
6. For qualifying transcripts, invoke only execute_supervised with complete
   analysis_gate, or its authorized CLI equivalent.
7. Verify exact provider records by independent readback before COMPLETE.

A missing authority, unsupported connector, conflicting rule, or missing
evidence blocks the requested operation while preserving last confirmed state.
Read-only classification is not proof that a read was performed. A result of
PREFLIGHT_REQUIRED is never a successful processing receipt.

## Account-wide limitations

Repository code cannot automatically intercept ordinary ChatGPT conversations.
An account-level conversational instruction may ask ChatGPT to recognize
commands, but it cannot guarantee deterministic invocation, tool access,
authorization, or persistence. Deployment requires a separately supported
ChatGPT entrypoint and authenticated handoff. Do not claim one is installed.

## Phase 1 tests and rollback

Run: PYTHONPATH=src python -m unittest discover -s tests/unit -p
'test_trigger_router.py' -v

Test normal chat, explicit commands, direct pasted transcript/link candidates, quote/untrusted content, opt-out,
unknown commands, invalid provenance and oversized input. This does not test
host authentication, ChatGPT-wide behavior, live providers, or independent
readback. Rollback: revert the Phase 1 feature-branch changes. No provider
records or durable receipts are created by the router.
