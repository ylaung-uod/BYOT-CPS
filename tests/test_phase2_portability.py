import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import create_templates
import create_topology
from export_project import export


class PhaseTwoPortabilityTests(unittest.TestCase):
    def test_live_host_access_readback_requires_exact_tap_and_management_link(self):
        nodes = [
            {
                "name": "HOST-ACCESS",
                "node_id": "host-id",
                "properties": {
                    "ports_mapping": [
                        {
                            "interface": "tap-browser",
                            "name": "tap-browser",
                            "port_number": 0,
                            "type": "ethernet",
                        }
                    ]
                },
            },
            {"name": "MGMT-SWITCH", "node_id": "mgmt-id"},
            {"name": "DMZ-SWITCH", "node_id": "dmz-id"},
        ]
        links = [
            {
                "nodes": [
                    {"node_id": "host-id", "adapter_number": 0, "port_number": 0},
                    {"node_id": "mgmt-id", "adapter_number": 0, "port_number": 2},
                ]
            }
        ]
        checker = getattr(create_topology, "host_access_matches", None)
        if checker is None:
            self.fail("create_topology.host_access_matches is missing")
        self.assertTrue(checker(nodes, links, "tap-browser"))
        self.assertFalse(checker(nodes, links, "wrong-tap"))

        nodes_with_extra_mapping = json.loads(json.dumps(nodes))
        nodes_with_extra_mapping[0]["properties"]["ports_mapping"].append(
            {"interface": "eth0", "name": "eth0", "port_number": 1, "type": "ethernet"}
        )
        self.assertFalse(checker(nodes_with_extra_mapping, links, "tap-browser"))

        wrong_link = json.loads(json.dumps(links))
        wrong_link[0]["nodes"][1]["node_id"] = "dmz-id"
        self.assertFalse(checker(nodes, wrong_link, "tap-browser"))

    def test_topology_provenance_matches_management_host_access_revision(self):
        topology_bytes = (ROOT / "topology.json").read_bytes()
        topology = json.loads(topology_bytes)
        provenance = json.loads((ROOT / "provenance.json").read_text())
        self.assertEqual(
            provenance["generated_topology_sha256"],
            hashlib.sha256(topology_bytes).hexdigest(),
        )
        self.assertEqual(provenance["node_count"], len(topology["nodes"]))
        self.assertEqual(provenance["link_count"], len(topology["links"]))

    def test_exporter_preserves_synthetic_management_host_access(self):
        source = {
            "name": "source",
            "scene_height": 1000,
            "scene_width": 2000,
            "show_grid": True,
            "show_interface_labels": False,
            "show_layers": False,
            "snap_to_grid": True,
            "topology": {
                "nodes": [
                    {
                        "name": "PURPLE-SWITCH",
                        "node_id": "mgmt-switch",
                        "node_type": "ethernet_switch",
                        "x": -180,
                        "y": -105,
                        "z": 1,
                        "symbol": ":/symbols/ethernet_switch.svg",
                        "properties": {"ports_mapping": []},
                    }
                ],
                "links": [],
            },
        }
        with tempfile.NamedTemporaryFile("w", suffix=".gns3") as stream:
            json.dump(source, stream)
            stream.flush()
            exported = export(stream.name)
        host_access = next(
            node for node in exported["nodes"] if node["name"] == "HOST-ACCESS"
        )
        self.assertEqual(host_access["properties"]["ports_mapping"][0]["interface"], "${MGMT_INTERFACE}")
        self.assertIn(
            {"HOST-ACCESS", "MGMT-SWITCH"},
            [{endpoint["node"] for endpoint in link["nodes"]} for link in exported["links"]],
        )

    def test_exporter_rejects_management_port_two_reuse(self):
        source = {
            "name": "source",
            "scene_height": 1000,
            "scene_width": 2000,
            "show_grid": True,
            "show_interface_labels": False,
            "show_layers": False,
            "snap_to_grid": True,
            "topology": {
                "nodes": [
                    {
                        "name": "PURPLE-SWITCH",
                        "node_id": "mgmt-switch",
                        "node_type": "ethernet_switch",
                        "x": 0,
                        "y": 0,
                        "properties": {"ports_mapping": []},
                    },
                    {
                        "name": "OTHER-SWITCH",
                        "node_id": "other-switch",
                        "node_type": "ethernet_switch",
                        "x": 100,
                        "y": 0,
                        "properties": {"ports_mapping": []},
                    },
                ],
                "links": [
                    {
                        "nodes": [
                            {
                                "node_id": "mgmt-switch",
                                "adapter_number": 0,
                                "port_number": 2,
                            },
                            {
                                "node_id": "other-switch",
                                "adapter_number": 0,
                                "port_number": 0,
                            },
                        ]
                    }
                ],
            },
        }
        with tempfile.NamedTemporaryFile("w", suffix=".gns3") as stream:
            json.dump(source, stream)
            stream.flush()
            with self.assertRaisesRegex(SystemExit, "MGMT-SWITCH port 2"):
                export(stream.name)

    def test_management_interface_placeholder_resolves_from_environment(self):
        original = dict(create_topology.os.environ)
        try:
            create_topology.os.environ["MGMT_INTERFACE"] = "tap-browser"
            resolved = create_topology.resolve(
                {"interface": "${MGMT_INTERFACE}", "name": "${MGMT_INTERFACE}"}
            )
        finally:
            create_topology.os.environ.clear()
            create_topology.os.environ.update(original)
        self.assertEqual(
            resolved,
            {"interface": "tap-browser", "name": "tap-browser"},
        )

    def test_management_host_access_cloud_is_connected_only_to_management(self):
        topology = json.loads((ROOT / "topology.json").read_text())
        host_access = next(
            node for node in topology["nodes"] if node["name"] == "HOST-ACCESS"
        )
        self.assertEqual(host_access["node_type"], "cloud")
        self.assertEqual(
            host_access["properties"]["ports_mapping"],
            [
                {
                    "interface": "${MGMT_INTERFACE}",
                    "name": "${MGMT_INTERFACE}",
                    "port_number": 0,
                    "type": "ethernet",
                }
            ],
        )
        host_links = [
            {endpoint["node"] for endpoint in link["nodes"]}
            for link in topology["links"]
            if any(endpoint["node"] == "HOST-ACCESS" for endpoint in link["nodes"])
        ]
        self.assertEqual(host_links, [{"HOST-ACCESS", "MGMT-SWITCH"}])


    def test_tracked_files_exclude_private_host_identifiers(self):
        tracked = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout.split(b"\0")
        forbidden_literals = (b"/home/" + b"yll", b"Res" + b"rc_")
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
            "MGMT_INTERFACE",
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

    def test_management_browser_access_setup_is_documented(self):
        quickstart = (ROOT / "QUICKSTART.md").read_text()
        self.assertIn("ip tuntap add dev byot-mgmt mode tap", quickstart)
        self.assertIn("ip addr add 192.168.99.2/24 dev byot-mgmt", quickstart)
        self.assertIn("https://192.168.99.1/", quickstart)
        self.assertIn("HOST-ACCESS", quickstart)
        self.assertIn("MGMT-SWITCH", quickstart)
        self.assertIn("not bridged to a physical", quickstart)


if __name__ == "__main__":
    unittest.main()
