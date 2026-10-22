"""Host-side, disposable Docker execution. Does not grant full acceptance."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "python:3.12-slim"


def command(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True,
                          timeout=kwargs.pop("timeout", 60), **kwargs).stdout.strip()


def validate_container(info, stage):
    host = info["HostConfig"]
    mounts = info["Mounts"]
    binds = [mount for mount in mounts if mount["Type"] == "bind"]
    other_mounts_safe = all(mount["Type"] == "bind" or
                            (mount["Type"] == "tmpfs" and mount["Destination"] == "/tmp")
                            for mount in mounts)
    return {
        "network_none": host["NetworkMode"] == "none",
        "root_filesystem_readonly": host["ReadonlyRootfs"] is True,
        "unprivileged": host["Privileged"] is False,
        "capabilities_dropped": host["CapDrop"] == ["ALL"],
        "no_extra_capabilities": not host.get("CapAdd"),
        "no_new_privileges": any(s in ("no-new-privileges", "no-new-privileges:true") for s in host.get("SecurityOpt", [])),
        "unprivileged_user": info["Config"]["User"] == "65534:65534",
        "only_readonly_source_mount": len(binds) == 1 and other_mounts_safe
            and binds[0]["Source"] == str(stage) and binds[0]["Destination"] == "/sandbox"
            and binds[0]["RW"] is False,
        "temporary_storage_only": set(host.get("Tmpfs", {})) == {"/tmp"},
        "bounded_resources": host["PidsLimit"] == 128 and host["Memory"] == 512 * 1024 * 1024
            and host["NanoCpus"] == 1000000000,
        "private_namespaces": host.get("PidMode", "") != "host" and host.get("IpcMode", "") != "host",
        "no_devices": not host.get("Devices"),
    }


def stage_sources(stage):
    stage.mkdir()
    stage.chmod(0o755)
    manifest = {}
    for directory in ("src", "tests", "tools"):
        for source in sorted((ROOT / directory).rglob("*")):
            if "__pycache__" in source.parts:
                continue
            if source.is_symlink():
                raise ValueError("Source symlinks are outside runner scope")
            if source.is_file() and source.suffix in (".py", ".sql", ".json"):
                data = source.read_bytes()
                if len(data) > 2 * 1024 * 1024:
                    raise ValueError("Unexpected source size")
                relative = source.relative_to(ROOT)
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                target.chmod(0o644)
                manifest[str(relative)] = hashlib.sha256(data).hexdigest()
    return manifest


def main():
    report = {"schema_version": 1, "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "isolated_run_status": "BLOCKED", "full_acceptance_status": "BLOCKED",
              "limitations": ["shared container kernel; trusted GitHub-hosted VM/engine",
                              "no independent human reviewer or verified repository log-retention deadline",
                              "no external adapters, concurrency, lease fencing or production acceptance"],
              "source_commit": os.environ.get("SOURCE_SHA"),
              "github_run_id": os.environ.get("GITHUB_RUN_ID"),
              "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
              "provider_identity_assertion": os.environ.get("RUNNER_ENVIRONMENT", "unverified"),
              "container_removed": False, "source_staging_removed": False}
    container = None
    temporary = None
    try:
        if not shutil.which("docker"):
            raise RuntimeError("Docker executable unavailable; no isolated tests attempted")
        source_sha = report["source_commit"]
        if not source_sha or not re.fullmatch(r"[0-9a-f]{40}", source_sha):
            raise RuntimeError("Exact source commit required")
        if command(["git", "-C", str(ROOT), "rev-parse", "HEAD"]) != source_sha:
            raise RuntimeError("Checkout does not match requested source commit")
        command(["docker", "pull", IMAGE], timeout=120)
        image = json.loads(command(["docker", "image", "inspect", IMAGE]))[0]
        image_id = image["Id"]
        report["image_id"] = image_id
        report["image_repository_digests"] = image.get("RepoDigests", [])
        temporary = tempfile.TemporaryDirectory(prefix="nexus-isolated-")
        # The container user must traverse the parent directory to read its mount.
        Path(temporary.name).chmod(0o755)
        stage = Path(temporary.name) / "source"
        report["source_sha256"] = stage_sources(stage)
        container = "nexus-acceptance-" + uuid4().hex
        command(["docker", "create", "--name", container, "--network", "none", "--read-only",
                 "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true", "--user", "65534:65534",
                 "--pids-limit", "128", "--memory", "512m", "--cpus", "1",
                 "--tmpfs", "/tmp:rw,noexec,nosuid,size=128m,mode=1777",
                 "--mount", "type=bind,src=" + str(stage) + ",dst=/sandbox,readonly",
                 "--workdir", "/sandbox", "--env", "PYTHONDONTWRITEBYTECODE=1",
                 "--env", "PYTHONPATH=/sandbox/src", image_id, "python3", "-B", "/sandbox/tools/container_probe.py"])
        info = json.loads(command(["docker", "inspect", container]))[0]
        checks = validate_container(info, stage)
        report["host_container_preflight"] = checks
        if not all(checks.values()):
            raise RuntimeError("Container configuration failed closed before execution")
        output = command(["docker", "start", "--attach", container], timeout=180)
        report["container_result"] = json.loads(output)
        state = json.loads(command(["docker", "inspect", container]))[0]["State"]
        report["exit_code"] = state["ExitCode"]
        result = report["container_result"]
        if (state["ExitCode"] != 0 or not result.get("tests_attempted")
                or not result.get("container_preflight") or not all(result["container_preflight"].values())
                or result["local_report"]["local_test_status"] != "PASSED"
                or result["local_report"]["source_sha256"] != report["source_sha256"]):
            raise RuntimeError("Isolated tests or source-manifest comparison did not pass")
        report["isolated_run_status"] = "PASSED"
    except Exception as error:
        # Never dump the host environment or unfiltered docker inspect output.
        report["blocker"] = type(error).__name__ + (": " + str(error) if isinstance(error, (ValueError, RuntimeError)) else "")
        report["isolated_run_status"] = "BLOCKED"
    finally:
        if container:
            try:
                command(["docker", "rm", "--force", container])
                remaining = command(["docker", "ps", "--all", "--quiet", "--filter", "name=^/" + container + "$"])
                report["container_removed"] = not remaining
            except Exception:
                report["cleanup_error"] = "Container removal not confirmed"
        if temporary:
            staging_path = Path(temporary.name)
            temporary.cleanup()
            report["source_staging_removed"] = not staging_path.exists()
        if report["isolated_run_status"] == "PASSED" and not (report["container_removed"] and report["source_staging_removed"]):
            report["isolated_run_status"] = "BLOCKED"
        report["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
        print(json.dumps(report, sort_keys=True))
    return 0 if report["isolated_run_status"] == "PASSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
