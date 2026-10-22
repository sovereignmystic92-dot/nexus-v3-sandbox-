# Notion persistence adapter: bounded transport contract

This change depends on the unmerged mission-scenarios branch. It adds a credential-free adapter engine, a durable SQLite receipt/event journal and offline transport tests. It does not add a Notion SDK client, token, network transport, background worker, or coordinator integration. Existing runtime isolation stays intact. The hosted workflow is extended only to the exact notion-adapter branch.

## Binding and recovery

Each key binds an explicit sandbox parent, title and payload. The parent must match the operator-configured allowlist and a transport-observed synthetic sandbox marker. This is application scope, not server-side credential isolation. Synthetic labels are assertions; callers must supply fixture-only data.

Before creating, the transport must enumerate the bound root's direct children completely, including pagination and body-key inspection. A title search is insufficient. A matching existing record is independently fetched and compared by page ID, parent, key, title, exact payload and digest. Multiple matches, incomplete lookup or mismatched content hold without changing external records.

A durable CREATE_INTENT is committed before the external create. Its acknowledgment is saved separately from verification. A timeout, process interruption or missing response leaves an uncertain outcome. On retry the adapter reconciles existing records; it never automatically repeats a create after any persisted attempt/hold, even if lookup returns nothing. This deliberately favors a manual hold over duplicate risk. A known page ID is re-read directly. Mismatches are preserved for review; this adapter has no update/delete transport methods.

The receipt journal stores exact binding data and ordered observations. It provides local durability, not a cross-service transaction, tamper resistance, lease/fencing or multiworker exclusion. Use one worker and a durable private journal. Do not put real payloads or journals in the public repository.

## Validation and observation bridge

Offline tests cover normal create/readback/retry, response loss, simulated process interruption after create, absent delayed matches, read outage, changed binding, outside parent/key rejection, missing marker, incomplete lookup, duplicate matches, mismatches and retained history. The recorded-observation parser also checks child coverage, unknown/truncated blocks, title identity and the two inline-code encodings actually observed for the sandbox marker.

`tools/notion_observations.py` reads separately fetched Notion root/child observations from a private input file. Its transport cannot write. It checks that the supplied child IDs cover the root's rendered direct-child references; this is not proof of completeness of a service listing API or a transactionally consistent snapshot. The connected tools, used separately by the operator, performed the live writes.

The bounded N02 live exercise created one synthetic child, then fetched the root and all four direct children. The offline engine reconciled those actual recorded reads to the existing child without a create. A deliberate synthetic payload edit was read back, restored through the connected tool, and read back again. Evaluating the recorded mismatch produced MISMATCH; evaluating the restored record and repeating with the same journal produced VERIFIED with zero adapter create calls. The child was retained. No live response-loss or service-timeout injection occurred. Those cases passed only against the offline fake transport.

The first live root read rendered inline code as an HTML code tag, which the original parser rejected. That BLOCKED history was retained; support for both observed encodings and a regression test were added. No authorization requirement was relaxed.

The public summary excludes private Notion IDs, titles and fetched page bodies. Full private evidence belongs in the Notion sandbox. Current local validation: 49 distinct tests pass, including the four existing mission cases. Hosted results must be observed for this exact source revision before claiming an isolated pass. Prior run reports cover prior commits only.

## Remaining gates

No automatic Notion adapter is running. A future credentialed transport needs separately scoped credentials, bounded egress, complete API pagination, exact payload normalization, service error handling, uncertain-create reconciliation and an execution approval. It must not receive broad production credentials through the existing offline runner. Coordinator-to-external state mapping and durable checkpoint recovery across both systems remain unimplemented. Full integration acceptance, live lost-response behavior, concurrency, external reciprocal endpoints, long-term durability and independent human review remain pending.


## Observed hosted result

[Run 39858791522](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39858791522) passed at source commit `ece455fa8540eebbe85b32112ee9278dbbf1c736`. Retrieved completed job logs confirm 49 distinct unit/integration tests, including the 17 adapter/observation tests and four existing mission cases, passed. The four separately counted coordinator SIGKILL/disk-full checks also passed. All boundary checks, source matching and ordinary container/staging removal passed. GitHub reported 90-day retention, within policy. The exact synthetic report is in `hosted-run-39858791522.json`.

This supports the offline adapter contract and recorded-observation bridge only. The hosted container did not connect to Notion. The actual synthetic create/edit/restore was performed separately with connected tools, and its private reads were evaluated locally. Full integration acceptance remains BLOCKED. The evidence-only follow-up commit changes no tested runtime source. PR #2 and this dependent PR remain unmerged pending owner decisions.
