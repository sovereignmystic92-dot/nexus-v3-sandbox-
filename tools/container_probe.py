"""Container-internal checks before executing the synthetic suite."""

import errno
import io
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import socket
import sys


def main():
    status = dict(line.split(":", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":" in line)
    interfaces = sorted(p.name for p in Path("/sys/class/net").iterdir())
    routes = Path("/proc/net/route").read_text().splitlines()[1:]
    env_names = sorted(os.environ)
    forbidden = [key for key in env_names if any(s in key for s in ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"))
                 or key.startswith(("AWS_", "AZURE_", "GOOGLE_", "GITHUB_", "ACTIONS_", "RUNNER_"))]
    checks = {
        "nonroot_uid": os.getuid() == 65534,
        "capabilities_dropped": int(status["CapEff"].strip(), 16) == 0,
        "no_new_privileges": status["NoNewPrivs"].strip() == "1",
        "seccomp_enabled": status["Seccomp"].strip() == "2",
        "loopback_only": interfaces == ["lo"],
        "no_default_ipv4_route": not any(line.split()[1] == "00000000" for line in routes),
        "no_credential_env_names": not forbidden,
        "no_docker_socket": not Path("/var/run/docker.sock").exists(),
        "no_repository_git_directory": not Path("/sandbox/.git").exists(),
    }
    # Only probe a numeric documentation address after the interface checks pass.
    checks["external_connect_denied"] = False
    if checks["loopback_only"] and checks["no_default_ipv4_route"]:
        try:
            with socket.socket() as client:
                client.settimeout(1)
                client.connect(("192.0.2.1", 443))
        except OSError as error:
            checks["external_connect_denied"] = error.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EACCES, errno.EPERM)
    try:
        Path("/sandbox/.write-probe").write_text("synthetic probe")
        checks["source_write_denied"] = False
    except OSError as error:
        checks["source_write_denied"] = error.errno in (errno.EROFS, errno.EACCES)
    if not all(checks.values()):
        print(json.dumps({"container_preflight": checks, "tests_attempted": False}))
        return 2
    sys.path.insert(0, "/sandbox/tools")
    import validate
    stream = io.StringIO()
    # No output path: the report crosses the boundary as stdout JSON only.
    with redirect_stdout(stream):
        outcome = validate.main()
    report = json.loads(stream.getvalue())
    print(json.dumps({"container_preflight": checks, "tests_attempted": True, "local_report": report}))
    return outcome


if __name__ == "__main__":
    raise SystemExit(main())
