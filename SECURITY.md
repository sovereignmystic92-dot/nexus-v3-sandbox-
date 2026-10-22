# Security boundaries

Public repository: synthetic data only. Never add real source transcripts, production identifiers, personal records, credentials, environment dumps, database files or raw operational logs.

The future runtime must have a disposable filesystem, test-only routing, no production credentials, no production mounts, disabled schedulers and no network or connector access. These are requirements, not verified properties of the current drafting environment. Application configuration alone cannot enforce host isolation.

No connector adapters or automatic workflows are proposed in this package. Repository protection, collaborator permissions and Actions settings require separate verification; they are not established by these files.

If sensitive material is found, stop publication, notify the repository owner privately, revoke any affected credential and review exposure. Do not post secrets in public issues. A private reporting channel has not been configured.
