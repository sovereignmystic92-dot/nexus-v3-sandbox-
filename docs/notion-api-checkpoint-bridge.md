# GitHub-to-Notion checkpoint bridge — inactive proposal

Compose NotionRequest (authenticated HTTPS) -> NotionCheckpointAPI (bounded REST
shapes) -> AuditCheckpointTransport (PR63 proposal) -> CheckpointAdapter ->
run_resumable. The transport proposal is not yet adopted or activated.

NotionRequest accepts a caller-supplied token and explicitly selected API version,
pins api.notion.com, refuses redirects/unbound paths, bounds response bytes and
timeouts, sanitizes failures and never retries. Both client and REST shape adapter
default to writes disabled. No token lookup, environment read or workflow is
installed. Host must independently verify credential identity, linkage, page scope
and current authority; possession of a token or successful GET is insufficient.

The REST adapter observes exact page UUID/inactive flags, enumerates top-level
children with bounded pagination, rejects repeated IDs, nested/partial inventory,
and exposes only JSON code blocks to checkpoint parsing. It does not claim full
rendering of arbitrary Notion pages or recursive sources. An audit with nested
blocks holds; do not weaken completeness to make a live run pass. Snapshot changes
during pagination are outside atomic consistency and require single-writer host
controls and reconciliation. PATCH adds one code block, chunked at 2000 characters
per text item, at most 100 items. A write reply is not verification.

Seven secret-free tests cover fetch/path binding, write defaults, pagination and
limits, nesting/duplicates/malformed inventory, chunking, lost acknowledgment,
client destination restrictions and sanitized transport failure without retries.
Mocks only: no actual Notion, credential or API-version compatibility established.
Reference API shapes: https://developers.notion.com/reference/get-block-children
and https://developers.notion.com/reference/request-limits .

Existing workflow notion-read-probe.yml references NOTION_SANDBOX_TOKEN and
NOTION_SANDBOX_ROOT_ID under protected environment notion-sandbox, read-only.
Do not repurpose it for writes. Current token value/capabilities, Foundation Audit
page access and environment settings were not inspected. No credentials may be
printed. No workflow, permission, scope or billing change is authorized here.

Proposed live sequence, after explicit review: confirm selected existing token's
bot identity and restricted page access without expanding them; if sufficient,
enroll one separately authorized synthetic checkpoint job on the approved audit;
run a single append/readback with both write switches explicitly enabled in a
reviewed protected workflow. Preserve native approval gates. If read-only or no
page access, stop and present the exact capability/access change for owner review.
Do not rotate/create credentials or broaden access automatically. Default state is
inactive; this document is not approval to execute or alter settings.
