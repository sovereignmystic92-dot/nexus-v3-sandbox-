# Archive recovery across a socket timeout

This is offline synthetic integration evidence. A local HTTP fixture withholds
the first append response until the real client socket times out. The unchanged
BoundClient, NotionArchivePort and ArchiveRecoveryHost execute the request,
record its unknown outcome, reopen SQLite and reconcile fresh observations.
This is distinct from the earlier post-success SIGKILL live probe.

The test-only opener accepts only the production client's pinned Notion origin
and a literal synthetic credential, strips Authorization, and routes to a
numeric loopback address with a 250 ms receive deadline. It never forwards a
real credential. The production endpoint, 20-second timeout, one-request write
budget, redirect rejection and no-retry behavior are unchanged. No workflow,
workflow fingerprint, credential route, permission, provider grant or schedule
changes are required. Existing isolated acceptance discovers tests/unit and can
run the fixture on loopback inside its existing network-none container.

| Server outcome at timeout | Required recovery |
| --- | --- |
| First chunk committed, response withheld | Fresh host sees it; writes only chunks 1 and 2; final exact readback performs zero writes. |
| First request settled without a commit | Repeated fresh hosts still block with zero new writes because listing absence supplies no settled-non-commit proof. |
| First request still pending, initially invisible | Fresh host blocks; after the original request commits, fresh readback resumes without duplicating chunk 0. |
| Readback fails after an uncertain committed write | Stop without any new append or promotion. |

All cases assert a real socket.timeout, a consumed write budget, durable
WRITE_INTENT followed by WRITE_OUTCOME_UNKNOWN, and no automatic retry.
Successful reconciliation requires exactly three server append requests in
index order [0, 1, 2], the original 645 bytes in exactly three chunks, and a final
read-only verification. No confirm_absent override is provided. Each attempt
constructs a new host and client and reopens the same SQLite journal; these
tests do not claim separate-process or cross-host execution.

Validation on the candidate: four new socket-fault tests, 19 existing probe
tests and 48 transcript tests passed locally (71 total). Commands:

```sh
PYTHONPATH=src python -m unittest discover -s tests/unit -p 'test_notion_archive*.py' -v
PYTHONPATH=src python -m unittest discover -s tests -p test_transcript_fidelity.py -v
```

Hosted CI remains required. No real Notion timeout, TLS failure, packet-loss
proxy, provider visibility guarantee, authenticated identity, distributed
fencing, full transcript-to-Cortex execution or unattended readiness follows.
Audit statuses are unchanged. No paid calls or live provider writes are made.
Rollback consists of removing this document and the new test file.
