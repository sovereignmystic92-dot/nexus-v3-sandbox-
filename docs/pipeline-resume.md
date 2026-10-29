# Opt-in pipeline resume draft

`run_resumable` preserves all seven stages, loads an explicitly provisioned
checkpoint and rejects missing state. Binding includes run, source identity/hash,
destination, policy, code compatibility revision and schema. It commits and reads
back pending intent before callbacks. A pending action uses observation-only
reconciliation; failure holds without automatic execution. Completed stages do
not execute again. Existing `run` remains a single-pass API.

The host must provision private durable custody, save/read independent copies,
authenticate authority and evidence, revalidate actual destinations and supply
truthful observation callbacks. Reconciliation must not perform mutations. This
callback contract cannot prevent a malicious callback or bypassing caller.
An empty checkpoint must be explicitly enrolled before first dispatch; missing
custody is never silently replaced. Policy/code changes require adjudication,
not simply rewriting saved bindings. Whole-checkpoint rollback/tampering,
multiple workers, live adapters and cross-host durability remain outside scope.

Six new local fixture tests cover completed no-op, prefix continuation,
misbinding/order rejection, lost acknowledgment and failed intent. An actual
three-process test uses a private synthetic fsynced checkpoint fixture: process
one exits after its effect, process two reconciles without replay, and process
three observes completion without callbacks. This does not provision durable
external storage or establish survival of host loss. The operation journal remains the
write-adapter contract; this receipt checkpoint does not replace provider-level
reconciliation or install a second provider writer. No live workflow routing or
mandatory interception is installed. This draft requires further validation and
independent review before adoption.
