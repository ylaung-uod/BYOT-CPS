import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class PhaseFourReproducibilityTests(unittest.TestCase):
    def test_both_dockerfiles_use_the_declared_ubuntu_snapshot(self):
        for image in ("ubuntu18-lab", "ubuntu24-lab"):
            with self.subTest(image=image):
                dockerfile = (ROOT / "Dockerfiles" / image / "Dockerfile").read_text()
                self.assertIn("ARG UBUNTU_SNAPSHOT=20260903T000000Z", dockerfile)
                self.assertIn("https://snapshot.ubuntu.com/ubuntu/${UBUNTU_SNAPSHOT}", dockerfile)
                self.assertIn("Acquire::Check-Valid-Until=false", dockerfile)
                self.assertIn("COPY isrg-root-x1.pem /etc/ssl/certs/ca-certificates.crt", dockerfile)
                self.assertNotIn("Verify-Peer=false", dockerfile)
        manifest = json.loads((ROOT / "container_images.json").read_text())
        expected_ca = manifest["bootstrap_ca_sha256"]
        self.assertEqual(expected_ca, "22b557a27055b33606b6559f37703928d3e4ad79f110b407d04986e1843543d1")
        for image in ("ubuntu18-lab", "ubuntu24-lab"):
            certificate = ROOT / "Dockerfiles" / image / "isrg-root-x1.pem"
            self.assertEqual(hashlib.sha256(certificate.read_bytes()).hexdigest(), expected_ca)

    def test_spdx_generator_records_exact_package_versions_deterministically(self):
        from generate_container_sboms import build_spdx_document

        declaration = {
            "key": "ubuntu18-lab",
            "image": "byot-cps/ubuntu18-lab:latest",
            "base": "ubuntu:18.04",
            "base_digest": "sha256:" + "1" * 64,
            "snapshot": "20260903T000000Z",
            "sbom": "sbom/ubuntu18-lab.spdx.json",
        }
        packages = [
            ("zlib1g:amd64", "1:1.2.11", "amd64"),
            ("bash", "4.4.18-2ubuntu1.3", "amd64"),
        ]
        first = build_spdx_document(declaration, packages)
        second = build_spdx_document(declaration, list(reversed(packages)))
        self.assertEqual(first, second)
        self.assertEqual(first["spdxVersion"], "SPDX-2.3")
        self.assertEqual(
            [(item["name"], item["versionInfo"]) for item in first["packages"][1:]],
            [("bash", "4.4.18-2ubuntu1.3"), ("zlib1g:amd64", "1:1.2.11")],
        )
        self.assertEqual(first["creationInfo"]["created"], "2026-09-03T00:00:00Z")
        self.assertEqual(first["packages"][0]["externalRefs"][0]["referenceLocator"], declaration["image"])
        json.dumps(first)

    def test_runtime_probe_policy_covers_phase_four_security_checks(self):
        from test_container_images import validate_probe

        declaration = {
            "ubuntu_version": "24.04",
            "default_user": "lab",
            "required_group": "sudo",
            "required_tools": ["curl", "ip", "ping", "sshd", "sudo", "tcpdump"],
            "allowed_listeners": ["tcp:22"],
            "allowed_processes": ["sleep", "sshd"],
        }
        probe = {
            "ubuntu_version": "24.04",
            "pid1_user": "lab",
            "groups": ["lab", "sudo"],
            "sudo_without_password": False,
            "sudo_with_password": True,
            "ssh": {
                "passwordauthentication": "yes",
                "permitrootlogin": "no",
                "usepam": "yes",
            },
            "tools": {name: True for name in declaration["required_tools"]},
            "listeners": ["tcp:22"],
            "processes": ["sleep", "sshd"],
            "suspicious_files": [],
        }
        self.assertEqual(validate_probe(declaration, probe), [])
        probe["sudo_without_password"] = True
        probe["listeners"].append("tcp:4444")
        probe["suspicious_files"].append("mirai")
        errors = validate_probe(declaration, probe)
        self.assertTrue(any("password" in error for error in errors))
        self.assertTrue(any("listener" in error for error in errors))
        self.assertTrue(any("suspicious" in error for error in errors))

    def test_makefile_exposes_sbom_and_runtime_verification_targets(self):
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn("container-sboms: docker-images", makefile)
        self.assertIn("src/generate_container_sboms.py", makefile)
        self.assertIn("container-sboms-check: docker-images", makefile)
        self.assertIn("src/generate_container_sboms.py --check", makefile)
        self.assertIn("container-runtime-test: docker-images", makefile)
        self.assertIn("src/test_container_images.py", makefile)

    def test_container_reproducibility_workflow_is_documented(self):
        documentation = "\n".join(
            (ROOT / path).read_text()
            for path in ("README.md", "docs/REPRODUCIBILITY.md", "docs/CONTAINERS.md")
        )
        for expected in (
            "20260903T000000Z",
            "container_images.json",
            "sbom/ubuntu18-lab.spdx.json",
            "sbom/ubuntu24-lab.spdx.json",
            "make container-sboms",
            "make container-sboms-check",
            "make container-runtime-test",
            "password-protected sudo",
            "only TCP port 22 listens",
            "APT also verifies",
            "Ubuntu-signed repository metadata",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, documentation)


if __name__ == "__main__":
    unittest.main()
