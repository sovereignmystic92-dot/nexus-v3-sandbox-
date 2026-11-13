# Skill Forge Wolfram plugin-derived pilot v0.1 (draft only)

Related: [issue #296](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/296).

## Evidence and rights
Wolfram plugin tool observed in the connected Chat environment: `WolframLanguageEvaluator` accepted `Factor[x^4 - 1]` and returned `Out[1]= (-1 + x)*(1 + x)*(1 + x^2)`. This is a bounded authenticated **tool invocation**, not a local Codex runtime or transferable source. Documentation: https://reference.wolfram.com/language/Wolfram/AgentTools/tutorial/QuickStartforAICodingApplications and https://reference.wolfram.com/language/ref/DeployAgentTools. The documentation describes a Codex-compatible MCP deployment, but does not establish that it is installed, licensed, or authorized for this repository.

The adapter here is **independently authored Python**, not Wolfram source code. It implements a strict request formatter for one documented Wolfram Language expression, a modified response normalizer, and a second local validator. Offline fixtures mirror the observed response. This is an intentionally narrow plugin-derived proof of concept, **not** a general symbolic engine or full Wolfram replacement.

## Run
```sh
PYTHONPATH=src python -m unittest discover -s tests/unit -p 'test_skill_forge_wolfram.py' -v
```

## Boundaries
- SQLite FULL synchronous local library with stable immutable IDs and canonical export. No Cortex or Notion writes.
- Fixture-only transport supplied by the test. No Wolfram API credentials, paid calls, remote execution, plugin installation, autonomous discovery or deployment.
- Explicit offline approval flag required for composition. Unsupported expressions and output fail closed.
- Readiness `offline-tested-only` is not production authorization.
- The validator checks only a bounded exact x^4-1 factorization fixture; general polynomial validation is **not** implemented.
- No local Wolfram runtime, independent review, or Codex execution environment verified.
- Rollback: close draft PR / delete feature branch; no external provider records changed.

## Acceptance evidence
CI must pass on the final exact commit. A real provider result was observed in a separate authenticated Chat invocation; offline tests must not be described as a live end-to-end Codex adaptation. Review rights/licensing, local Wolfram availability and composition extension before broader use.
