# CP08 real-container stop probe

The hosted acceptance job now runs a bounded probe after the ordinary suite. It invokes the real runner and real Docker with the same pinned image, network-none restrictions, source staging, ledger check and retention preflight. Only the container workload is replaced with a synthetic sleep. It waits for Docker Running=true, sends SIGTERM only to the owned runner PID and independently verifies the uniquely named container and staging directory are absent after the runner reports BLOCKED. A bounded parent fallback attempts container removal on probe failure; fallback removal cannot make failed primary evidence pass.

No Docker is available in the authoring environment, so local syntax/suite checks do not establish this hosted test. Workflow byte inventory is deliberately updated for the added step; no other workflow or trigger changes. No credentials, live service writes, provider artifacts or existing container are targeted.

This is catchable runner interruption, not host loss/SIGKILL, GitHub cancellation or future retention deletion. CP08 remains partial and 11/19 unchanged. Hosted results must be observed before acceptance. Merge requires owner approval.
