# Skill Forge Wolfram plugin-derived pilot v0.1 (draft only)

Related: [issue #296](https://github.com/sovereignmystic92-dot/nexus-v3-sandbox-/issues/296).

## Evidence and rights
Wolfram plugin tool observed in the connected Chat environment: `WolframLanguageEvaluator` accepted `Factor[x^4 - 1]` and returned `Out[1]= (-1 + x)*(1 + x)*(1 + x^2)`. This is a bounded authenticated **tool invocation**, not a local Codex runtime or transferable source. Documentation: https://reference.wolfram.com/language/Wolfram/AgentTools/tutorial/QuickStartforAICodingApplications and https://reference.wolfram.com/language/ref/DeployAgentTools. The documentation describes a Codex-compatible MCP deployment, but does not establish that it is installed, licensed, or authorized for this repository.

The independently authored Python adapter computes the two bounded factorizations by repeated difference of squares. The validator expands the parsed factors over integers and checks the resulting coefficients. The optional fixture callback supports offline normalization and rejection tests.

## Run
```sh
PYTHONPATH=src python -m unittest discover -s tests/unit -p 'test_skill_forge_wolfram.py' -v
```

## Boundaries
- SQLite FULL synchronous local library with stable immutable IDs and canonical export. No Cortex or Notion writes.
- Local computation is the default. Tests may inject fixture responses. No Wolfram API credentials, paid calls, remote execution, plugin installation, autonomous discovery or deployment.
- Explicit offline approval flag required for composition. Unsupported expressions and output fail closed.
- Readiness `offline-tested-only` is not production authorization.
- The request and validator support the x² − 1 and x⁴ − 1 fixtures. An unsupported request or incompatible skill version is rejected before transport.
- No local Wolfram runtime, independent review, or Codex execution environment verified.
- Rollback: close draft PR / delete feature branch; no external provider records changed.

The catalog records contracts, schemas, fixture and evidence references, adapter paths and dependency versions. Unavailable capabilities can be cataloged without execution permission. The previous draft manifests lack these required fields and should be rebuilt from the current descriptors for this offline pilot.

## Acceptance evidence
The existing Isolated synthetic acceptance workflow discovers the Skill Forge tests. The PR links evidence for the reviewed revision. A real provider result was observed in a separate authenticated Chat invocation; offline tests must not be described as a live end-to-end Codex adaptation. Review rights/licensing, local Wolfram availability and composition extension before broader use.

## Provider feasibility
Wolfram documents [Local MCP for Codex](https://www.wolfram.com/ai/mcp/local/) with an installed Wolfram application. The [Wolfram Engine FAQ](https://wolfram.com/engine/faq/) describes Community Edition as licensed for non-production use. This provides a candidate path for supervised development with a licensed installation. The intended runner and automation terms, installed runtime, and actual Codex tool invocation remain to be verified before a provider-backed run.
