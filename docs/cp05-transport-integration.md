# CP05 transport integration

CP05 remains PARTIALLY_VERIFIED; tracker stays 11/19. No requirement or scope change.

The legacy CortexToolTransport is now read-only: create/update fail before any provider invocation. Historical C05/C06/C11 probes still instantiate this bridge, so their old writer modes now stop rather than replay without bindings. Their original historical evidence is retained. Read-only reconciliation remains available.

Existing enrolled-fixture updates use BoundCortexToolTransport explicitly. New integration tests invoke it through CortexAdapter: one exact update verifies, reopening/repeating performs no duplicate update and preserves target identity; wrong root ownership cannot verify or mutate. Offline test transports remain usable for unit tests. Direct host tool access and arbitrary user-supplied transports are not controlled by this library.

210 local tests passed. Hosted checks and exact committed-source readback are required before merge. This change intentionally removes unbound host mutation capability; creating new fixtures requires a separately verified enrollment path, not silently reverting to the old bridge.

Caller/account identity remains an external prerequisite: currently exposed Cortex tools provide module ownership but no authenticated-caller introspection. Ownership/root existence does not prove the executing principal or provider-enforced grants. No live guarded update or complete host enrollment/routing assurance is claimed. Sequential checks are not CAS. Production remains paused and this does not close checkpoint twelve.
