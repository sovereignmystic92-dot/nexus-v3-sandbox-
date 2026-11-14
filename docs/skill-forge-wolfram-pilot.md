# Skill Forge Wolfram plugin-derived pilot v0.1 (draft only)

Related: [issue #296](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/296).

## Evidence and rights
Wolfram plugin tool observed in the connected Chat environment: `WolframLanguageEvaluator` accepted `Factor[x^4 - 1]` and returned `Out[1]= (-1 + x)*(1 + x)*(1 + x^2)`. This is a bounded authenticated **tool invocation**, not a local Codex runtime or transferable source. Documentation: https://reference.wolfram.com/language/Wolfram/AgentTools/tutorial/QuickStartforAICodingApplications and https://reference.wolfram.com/language/ref/DeployAgentTools. The documentation describes a Codex-compatible MCP deployment, but does not establish that it is installed, licensed, or authorized for this repository.

The adapter here is **independently authored Python**, not Wolfram source code. It implements a strict request formatter for two bounded Wolfram Language expressions, a modified response normalizer, and a second local validator. Offline fixtures mirror the observed response. This is an intentionally narrow plugin-derived proof of concept, **not** a general symbolic engine or full Wolfram replacement.

## Run
```sh
PYTHONPATH=src python -m unittest discover -s tests/unit -p 'test_skill_forge_wolfram.py' -v
```

## Boundaries
- SQLite FULL synchronous local library with stable immutable IDs and canonical export. No Cortex or Notion writes.
- Fixture-only transport supplied by the test. No Wolfram API credentials, paid calls, remote execution, plugin installation, autonomous discovery or deployment.
- Explicit offline approval flag required for composition. Unsupported expressions and output fail closed.
- Readiness `offline-tested-only` is not production authorization.
- The request and validator support the x² − 1 and x⁴ − 1 fixtures. An unsupported request or incompatible skill version is rejected before transport.
- No local Wolfram runtime, independent review, or Codex execution environment verified.
- Rollback: close draft PR / delete feature branch; no external provider records changed.

## Acceptance evidence
The existing Isolated synthetic acceptance workflow discovers the Skill Forge tests. [Run 43639974389](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/actions/runs/43639974389) recorded 11 passing Skill Forge tests at `68c5d24545944f3df2bf65235e2e098c2f719b24`, including catalog recovery in a fresh process. Final-revision CI remains required. A real provider result was observed in a separate authenticated Chat invocation; offline tests must not be described as a live end-to-end Codex adaptation. Review rights/licensing, local Wolfram availability and composition extension before broader use.

## Provider feasibility
Wolfram documents [Local MCP for Codex](https://www.wolfram.com/ai/mcp/local/) with an installed Wolfram application. The [Wolfram Engine FAQ](https://wolfram.com/engine/faq/) describes Community Edition as licensed for non-production use. This provides a candidate path for supervised development with a licensed installation. The intended runner and automation terms, installed runtime, and actual Codex tool invocation remain to be verified before a provider-backed run.
