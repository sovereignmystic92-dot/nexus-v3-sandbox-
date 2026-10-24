# Local recovery candidate — operating scope

This review candidate adds opt-in recovery/checkpoint helpers to the accepted single-worker sandbox. It does not replace the core adapter, provide backend fencing or implement an independently trusted latest-checkpoint authority.

Use disposable synthetic fixtures. Keep exactly one worker. Missing or conflicting journal/inventory/checkpoint evidence must hold operations until resolved through the helper's explicit recovery procedure. Preserve files after uncertain failures. Do not infer success from a visible restored journal.

The candidate retains cleanup-path protections, directory sync retry behavior, pending-marker recommit, backup sync before catalog publication and restored-directory sync before completion. These are local application guarantees within tested assumptions, not physical device-loss assurance.

Source baseline: 2f845d24bdb455ca5685bc1bf23f6eebcd7c825b.
Saved candidate unit result: 153 tests; suites overlap historical results and must not be summed.
Existing CI discovers all tests under tests/unit and performs the original four coordinator fault checks. It does not automatically execute the separate local guard/restore process-kill tools.

Full foundation acceptance remains blocked. Restricted identity/grant verification and multi-worker fencing remain deferred. Independent human review remains unavailable. Notion remains authoritative and paused; no production/canonical integration is authorized.

This candidate is a review addition only. Passing CI would provide bounded hosted evidence for its exact source; it would not authorize merging, deployment or expansion of operating scope.
