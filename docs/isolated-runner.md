# Disposable hosted-runner setup

The owner authorized arranging an isolated runner on 2026-10-22. The workflow is scoped to pushes affecting source/tests/tools or the workflow on `foundation-audit-draft`. It does not merge the pull request or deploy anything. It uses GitHub's standard `ubuntu-24.04` hosted VM for this public repository, not a paid/larger/self-hosted runner. No cron schedule or new cloud account is configured.

## Boundary

The orchestration host fetches exact public source without an access token and downloads the official Python image before test execution. The pulled image ID and registry digest are recorded; the tag can change between runs, so image acquisition is not reproducibly pinned in the workflow. Container execution uses the resolved immutable image ID.

Only regular Python/SQL/JSON files from src/tests/tools are copied into a fresh staging directory; symlinks are rejected. The container receives that directory read-only. It has no Docker socket, repository .git directory, host credential mount, inherited host environment or production adapter. The container runs as UID/GID 65534 with capabilities dropped, no new privileges, read-only root, isolated network=none, private namespaces, resource limits and temporary /tmp storage. The Docker engine and VM are trusted infrastructure; containers share the host kernel.

Before running tests, the host inspects the container configuration. The container separately checks its effective UID/capabilities/seccomp, interfaces/routes, denied external connect, source-write denial, credential-variable names and absence of .git/Docker socket. Tests fail closed if checks fail. The source manifest inside must exactly match the host-staged manifest. These checks support the stated boundary; they are not an independent penetration test or a proof against container/kernel escapes.

The orchestrator removes the container and source staging directory and confirms both removals. A job timeout/cancellation relies on hosted VM teardown; the script's cleanup cannot be guaranteed if the host process is forcibly killed. Job timeout is ten minutes, container execution timeout three minutes. Output is synthetic JSON in workflow logs; no artifact upload or new storage allocation is configured. Repository log retention remains an administrator-controlled, unverified setting.

## Evidence and verdict

Local syntax and boundary tests can run in this environment. Docker is unavailable locally, so a successful hosted run must be observed separately. The workflow must be accepted by the GitHub integration and an Actions run must complete before runner availability or isolation can be claimed. A hosted run can report isolated_run_status=PASSED only after preflight, local tests, source matching and cleanup all pass.

Full acceptance remains separately BLOCKED: independent reviewer/log-retention evidence and the unimplemented external/concurrency cases are not created by installing a runner. The local suite's passing count is not an isolation verdict. See the current workflow run and its exact head SHA rather than treating this setup document as execution evidence.

Official basis: [GitHub hosted-runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners), [Docker network none](https://docs.docker.com/engine/network/drivers/none/).
