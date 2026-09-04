import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import create_templates


class PhaseTwoPortabilityTests(unittest.TestCase):
    def test_tracked_files_exclude_private_host_identifiers(self):
        tracked = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout.split(b"\0")
        forbidden_literals = (b"/home/" + b"yll", b"Resrc_" + b"Hermes")
        timestamped_private_name = re.compile(
            rb"[A-Za-z0-9._-]+-20[0-9]{12,}\.(?:xml|conf|json)"
        )
        findings = []
        for relative in filter(None, tracked):
            content = (ROOT / relative.decode()).read_bytes()
            if b"\0" in content:
                continue
            for literal in forbidden_literals:
                if literal in content:
                    findings.append(f"{relative.decode()}: {literal.decode()}")
            if timestamped_private_name.search(content):
                findings.append(f"{relative.decode()}: timestamped private filename")
        self.assertEqual(findings, [])

    def test_makefile_declares_every_host_specific_input(self):
        makefile = (ROOT / "Makefile").read_text()
        for variable in (
            "GNS3_SERVER_CONFIG",
            "QEMU_PATH",
            "GNS3_QEMU_IMAGES",
            "IOT_INTERFACE",
            "PROJECT_NAME",
            "PFSENSE_CONFIG",
        ):
            with self.subTest(variable=variable):
                self.assertRegex(makefile, rf"(?m)^{variable} \?=")
                self.assertIn(f"$({variable})", makefile)

    def test_qemu_executable_is_a_runtime_template_parameter(self):
        declarations = json.loads((ROOT / "gns3_templates.json").read_text())["templates"]
        pfsense = next(item for item in declarations if item["key"] == "pfsense")
        self.assertEqual(pfsense["payload"]["qemu_path"], "${QEMU_PATH}")
        resolver = getattr(create_templates, "resolve_declarations", None)
        if resolver is None:
            self.fail("create_templates.resolve_declarations is missing")
        resolved = resolver(
            declarations,
            environment={"QEMU_PATH": "/portable/qemu-system-x86_64"},
        )
        resolved_pfsense = next(item for item in resolved if item["key"] == "pfsense")
        self.assertEqual(
            resolved_pfsense["payload"]["qemu_path"],
            "/portable/qemu-system-x86_64",
        )

    def test_documented_topology_example_uses_portable_iot_default(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("IOT_INTERFACE=docker0 make topology", readme)
        self.assertNotRegex(readme, r"IOT_INTERFACE=enx[0-9a-f]+")


if __name__ == "__main__":
    unittest.main()
