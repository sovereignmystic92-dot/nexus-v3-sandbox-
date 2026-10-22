# Notion API request mapping

`NotionRESTTransport` implements the adapter transport methods using an explicitly injected authenticated request gateway. It constructs relative endpoint paths and pins `Notion-Version` to `2026-03-11`. It does not load credentials, open sockets, install an SDK, invoke the connected ChatGPT tools, or start a worker. No direct API requests were made during this change.

The gateway contract is `request(method, relative_path, query=..., body=..., headers=...) -> decoded successful JSON object`. Before any live execution, a separate reviewed gateway must enforce the sole origin `https://api.notion.com/v1`, TLS, bounded timeouts/response sizes, protected credentials and no automatic POST retries. A dedicated test-root credential is not configured. The existing hosted runner stays offline.

## Behavior implemented

- Retrieve page metadata and check identity and direct parent before reading child content.
- Enumerate every root child across bounded pagination, rather than using title search. At most ten pages of up to 100 blocks per block enumeration and 200 total gateway requests per transport instance. Missing or looping cursors, duplicate blocks and unsupported/nested content hold instead of claiming a complete lookup.
- Inspect every direct child and parse exactly one adapter JSON record where present; check literal title identity, typed synthetic flag and plain payload. Ordinary paragraph page mentions are read as text, never executed. Literal record and title fields do not accept mention objects.
- Create only beneath the bound root, after observing its exact marker again. Construct one JSON code block, with rich text chunks no longer than 1,500 characters and at most 100 chunks. Bound title and payload size, including escaped JSON expansion. No update/delete endpoint is implemented.
- Return write acknowledgments to the receipt engine; require independent readback before VERIFIED. Errors, 429 responses and timeouts are not retried automatically. Unknown outcomes use the engine's existing reconciliation hold.

These are application controls over request construction. The injected gateway and credential still determine actual service access. Pagination observations are not a transactionally consistent snapshot; concurrent writers, service index delays and external atomicity remain outside this single-worker implementation.

## Evidence boundary

Local suite: 63 distinct tests passed, including 14 new REST-mapping tests. Tests exercise a decoded-response fake gateway with create/readback/retry, simulated lost POST acknowledgment, pagination and cursor failures, rate-limit response, wrong parent before body read, outside-target denial, unsupported/nested blocks, malformed records, Unicode chunk roundtrip, JSON escape expansion, request budget and literal mentions. Existing adapter checks were tightened to reject integer values masquerading as boolean flags.

These responses are synthetic test fixtures shaped from official documentation. They are not captured service responses or proof that live API permissions/version compatibility work. The prior tool-mediated N01/N02 results and the recorded-read bridge remain separate evidence. Hosted results for this exact source must be observed before claiming an isolated pass. No additional live Notion writes, credentials or network access were introduced.

Remaining work: secure gateway binding, separately verified test-only credential scope, bounded live API create/read/reconcile and cross-system coordinator checkpoint mapping. Full Notion integration acceptance remains BLOCKED. PRs 2 and 3 remain unmerged.

## Primary references checked

- [Retrieve block children](https://developers.notion.com/reference/get-block-children): list response pagination and API version header.
- [Retrieve a page](https://developers.notion.com/reference/retrieve-a-page): page metadata retrieval.
- [Block reference](https://developers.notion.com/reference/block): child-page, code and rich-text block structure.
- [Working with page content](https://developers.notion.com/guides/data-apis/working-with-page-content): page-parent creation, title and children payload, and `2026-03-11` examples.

References checked on 2026-10-22. Bounds in this implementation are intentionally restrictive application limits, not an assertion of every service limit.


## Hosted evidence observed

[Run 39859737137](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/39859737137) passed at source commit `fff453d157e3b2de81986091791a6c4a30bff196`. Retrieved completed job logs confirm 63 distinct tests passed, including the 14 REST request-mapping tests, 17 prior adapter/parser tests and four mission cases. The four separately counted coordinator crash/disk-full cases also passed. Boundary checks, source matching and ordinary container/staging removal passed. GitHub reported 90-day retention, within policy. The exact synthetic report is in `hosted-run-39859737137.json`.

This was an offline test of request mapping and reconciliation with an injected fake gateway. It did not access the Notion API. Full integration acceptance remains BLOCKED. An evidence-only follow-up commit changes no tested runtime source. PRs 2 and 3 remain unmerged.
