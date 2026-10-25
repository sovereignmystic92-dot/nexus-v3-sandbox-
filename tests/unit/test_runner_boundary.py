"""Reject container configurations that could expose the host or credentials."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from run_isolated import validate_container, cleanup_staging
import tempfile
from types import SimpleNamespace


class RunnerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.stage = Path("/synthetic/stage")
        self.info = {
            "HostConfig": {"NetworkMode": "none", "ReadonlyRootfs": True, "Privileged": False,
                           "CapDrop": ["ALL"], "CapAdd": None, "SecurityOpt": ["no-new-privileges:true"],
                           "Tmpfs": {"/tmp": "rw,noexec,nosuid,size=128m,mode=1777",
                                     "/fault-storage": "rw,noexec,nosuid,size=4m,mode=1777"},
                           "PidsLimit": 128, "Memory": 512 * 1024 * 1024, "NanoCpus": 1000000000},
            "Config": {"User": "65534:65534"},
            "Mounts": [{"Type": "bind", "Source": str(self.stage), "Destination": "/sandbox", "RW": False}],
        }

    def test_bounded_configuration_including_expected_tmpfs_is_accepted(self):
        self.assertTrue(all(validate_container(self.info, self.stage).values()))
        self.info["Mounts"].append({"Type": "tmpfs", "Destination": "/tmp"})
        self.assertTrue(all(validate_container(self.info, self.stage).values()))

    def test_host_network_privilege_capability_or_pid_mode_is_rejected(self):
        for field, value in (("NetworkMode", "host"), ("Privileged", True), ("CapAdd", ["SYS_ADMIN"]),
                             ("PidMode", "host"), ("ReadonlyRootfs", False), ("SecurityOpt", [])):
            info = deepcopy(self.info)
            info["HostConfig"][field] = value
            with self.subTest(field=field):
                self.assertFalse(all(validate_container(info, self.stage).values()))

    def test_docker_socket_or_extra_host_mount_is_rejected(self):
        self.info["Mounts"].append({"Type": "bind", "Source": "/var/run/docker.sock",
                                    "Destination": "/var/run/docker.sock", "RW": True})
        self.assertFalse(all(validate_container(self.info, self.stage).values()))

    def test_writable_source_mount_or_root_identity_is_rejected(self):
        self.info["Mounts"][0]["RW"] = True
        self.assertFalse(all(validate_container(self.info, self.stage).values()))
        self.info["Mounts"][0]["RW"] = False
        self.info["Config"]["User"] = "0:0"
        self.assertFalse(all(validate_container(self.info, self.stage).values()))

    def test_staging_cleanup_failure_preserves_report_and_blocks_success(self):
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'evidence'
            marker.write_text('retained')
            def fail():raise OSError('sensitive host path must not be logged')
            report={'isolated_run_status':'PASSED','container_removed':True}
            cleanup_staging(SimpleNamespace(name=directory,cleanup=fail),report)
            self.assertEqual(report['isolated_run_status'],'BLOCKED')
            self.assertFalse(report['source_staging_removed'])
            self.assertTrue(marker.exists())
            self.assertNotIn('sensitive',str(report))

    def test_cleanup_requires_observed_absence_and_supports_retry(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        report={'isolated_run_status':'PASSED'}
        cleanup_staging(SimpleNamespace(name=temporary.name,cleanup=lambda:None),report)
        self.assertEqual(report['isolated_run_status'],'BLOCKED')
        self.assertFalse(report['source_staging_removed'])
        cleanup_staging(temporary,report)
        self.assertTrue(report['source_staging_removed'])
        self.assertEqual(report['isolated_run_status'],'BLOCKED')


if __name__ == "__main__":
    unittest.main()

