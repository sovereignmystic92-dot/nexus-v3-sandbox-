# CP05 bound fixture transport progress

Status: PARTIALLY_VERIFIED. The accepted tracker remains 11/19. The adopted requirement and scope are unchanged.

BoundCortexToolTransport is an opt-in transport for already enrolled synthetic fixtures. It pins module IDs, names, owner and parent; root version/content checksum/dependency list must match before each permitted read/update. Updates preflight the target and declared dependencies, send only content/dependency fields, and validate acknowledgment identity, metadata, exact payload and one-step version increment. Wrong binding/missing metadata/root drift holds before mutation. Unenrolled creation and root mutation are disabled. A bad post-write acknowledgment raises uncertainty without repair/retry.

Ten new offline cases cover exact use, wrong root and target binding, changed root version/marker, unbound names/dependencies, disabled creation, root/nonsynthetic writes, missing/archived metadata, and bad acknowledgment without duplicate write. Full local validation: 208 tests passed. Hosted results must be checked separately.

This does NOT complete CP05: module owner metadata is not authenticated caller/account identity. Provider-side identity/root evidence, actual host registration, safe positive/negative live routing and intended creation coverage remain open. Existing raw transports/probes are not automatically migrated; this opt-in wrapper cannot be described as guarding every current path. Sequential preflight is not provider CAS and does not exclude a race after the last read. Effective grants, fencing and production authority remain separate open gates.

No private provider/installation metadata is in these public sources. No live test fixture was changed by this addition. No default activation, credential changes, scheduler, requirement change or new gate pass follows.

## Additional read-only observation

Fresh Cortex dictionaries for the authorized synthetic root, source and target were evaluated through the new wrapper. Exact pinned readback matched; a deliberately wrong configured root ID held before any mutation. The callback permitted context_get only and made zero provider writes. This is a read-only replay of fresh service observations, not authenticated caller identity, live write testing, provider-side scope enforcement or an installed guarded transport. No identifiers or ownership metadata from those private observations are published here.
