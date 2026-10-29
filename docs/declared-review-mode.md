# Owner-accepted declared review mode — sandbox proposal

Decision: NXS-OWNER-DECLARED-ATTRIBUTION-20261029. Clearly labeled ChatGPT/Gemini
attribution is accepted by the owner for this single-worker sandbox; no
provider-authenticated identity is claimed.

tools/declared_review_gate.py consumes two review records bound through the
adopted review_binding.verify contract. It requires exact context/source/digest,
actual author and reviewer/session declarations, distinct non-author sessions and
records, PASS with no unresolved findings, initial independence attestation and
exposure disclosure. It accepts ChatGPT and Gemini labels without GitHub account
enrollment. Fake fixtures are tests, not actual agent submissions.

Result: OWNER_ACCEPTED_DECLARED_REVIEWS, evidence class
OWNER_ACCEPTED_DECLARED_ATTRIBUTION, identity SELF_DECLARED_NOT_PROVIDER_AUTHENTICATED.
dispatch_authorized remains false: this verifies the revised review requirement
only, while native checks, current authority, allowed destination, intent-before-
effect and independent readback still govern actual action. It cannot be mistaken
for authenticated approval. Existing native GitHub CLI remains unchanged; no
automatic workflow consumes these declared records yet.

Five local synthetic tests pass for both agent labels and missing/duplicate/self/
stale/misbound/unresolved/incorrect-label rejection. Live writer provenance is
owner-accepted self-declaration, not measured model authentication. No real
Gemini submission or live transcript has been tested by these fixtures.

Next-event live test is PENDING until an actual user-supplied transcript/source
and authorized destination are observed through a supported trigger/session.
A future chat message is not a provisioned unattended webhook. Do not substitute
the historical research handoff or invent a transcript, review, result or closure.
Use one exact source, two real attributed reviews, current bindings, saved intent,
one authorized operation, separate readback and uncertain-outcome reconciliation.
Close only this bounded integration test after actual success, not CP02/CP09,
production or the whole foundation audit.

No credentials, accounts, permissions, protections, scheduler or workflow changes.
No provider invocation, Cortex write, production or CP09 activation. Keep draft
pending independent security review and applicable exact-revision checks.
