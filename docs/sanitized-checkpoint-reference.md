# Sanitized sandbox checkpoint reference

The owner limited the public repository to sandbox code, tests and sanitized evidence. Full checkpoint routing, provider IDs, installation identity and recovery payload remain in the authorized Notion/Cortex test records. No rejected private manifest is published here.

Public schema 2 contains only checkpoint sequence, UTC date, source commit, previous public entry hash and a SHA-256 commitment to the private manifest. The latest reference pins the final public entry. Exact-field validation refuses provider/installation/payload fields. This is a materially reduced disclosure: the public commitment cannot reconstruct its high-entropy private manifest or provide provider routing/access.

Migration is permitted only from the previously uninitialized schema-1 ledger. Existing initialized history cannot be rewritten or downgraded. Host preflight compares against the exact fetched GitHub base. The private binding verifier requires that the private manifest hashes to the current public commitment, the checkpoint sequence agrees, both observed provider IDs match private routing and both packet copies match the committed private packet hash.

198 local tests pass. Code and the initial sanitized reference are candidates until GitHub checks and merge/readback succeed. The first private paired recovery observation already passed; current-reference recovery must be retested from fresh provider reads after adoption. Full CP06 acceptance is NOT implied. The audit count stays 10/19.

Trust remains in the current GitHub service/reference and reviewed checker. Compromised administration, malicious removal of validation, physical faults, provider outage and indefinite retention are outside these observations. No production activation or unattended execution is added.
