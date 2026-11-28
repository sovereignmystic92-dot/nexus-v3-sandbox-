# Private Haiti replay on a fresh runner

Status: proposed manual runner; not executed on GitHub Actions. Follows PR 318.

Local recovery matched all three frozen finding IDs and payload digests against the exact canonical Notion source revision. The original database was preserved. A changed source was rejected. This does not establish independent analytical review, factual corroboration, Cortex persistence or unattended access.

The proposed workflow uses the existing `notion-sandbox` environment and its `NOTION_SANDBOX_TOKEN`. The new protected data input `CSF_HAITI_BATCH_B64` would hold the base64 encoding of the recovered 16,384-byte SQLite database, not a new API credential. Its SHA-256 is pinned in the driver. The database includes private candidate assertions and assigned claim IDs; it must never appear in Git, workflow inputs, logs or public artifacts.

## Before activation

1. Review this exact revision, including the workflow, source read and disclosure boundary. No independent review is claimed by the implementing author.
2. Obtain owner authorization before transferring the recovered database into the protected GitHub environment. This PR does not create or change secrets or grant runner access to that batch.
3. Configure only the approved protected batch input, then manually invoke the reviewed workflow on main with `replay_confirmed=true`.
4. Check the actual run's checkout, source revision/digest, database digest, finding references and metadata-only logs. A green offline check alone is not runner acceptance.

The workflow checks out both its driver at the exact dispatch SHA and the original implementation at `616eb0690673d9f0ebe4253a61f33e23aa574932`. Missing or changed batch data is rejected before a Notion read. The source is read twice around content retrieval and must retain its pinned revision and digest. The restored database and source envelope live only in a private temporary directory and are removed on ordinary exit. Forced runner termination cleanup remains a hosted-runner retention assumption. No source or database artifact is uploaded.

Success emits only fixed finding IDs, hashes, source revision and run provenance. Child/provider exceptions are not echoed. No Gemini call, Notion/Cortex write, review verdict, audit promotion, schedule or production activation is included.

Rollback: close this draft PR. If activated later, disable the workflow and remove the batch data input under the applicable approval process; leave the canonical Notion source and retained recovery package intact.

Validation: `python -m unittest discover -s tests/unit -p 'test_csf_private_runner_replay.py' -v`. The draft driver was also run locally against the actual recovered database and verified source; that local run is separate from GitHub runner acceptance.
