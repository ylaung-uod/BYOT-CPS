import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProjectNamingTests(unittest.TestCase):
    def test_default_gns3_project_name_is_byot_cps(self):
        makefile = (ROOT / "Makefile").read_text()
        topology_builder = (ROOT / "src/create_topology.py").read_text()
        topology = json.loads((ROOT / "topology.json").read_text())
        self.assertIn("PROJECT_NAME ?= byot-cps", makefile)
        self.assertIn('default="byot-cps"', topology_builder)
        self.assertEqual(topology["project"]["name"], "byot-cps")

    def test_gns3_node_templates_use_byot_cps_namespace(self):
        templates = json.loads((ROOT / "gns3_templates.json").read_text())["templates"]
        for item in templates:
            self.assertTrue(item["name"].startswith("byot-cps - "), item["name"])
            self.assertEqual(item["payload"]["name"], item["name"])
        docker_images = [item["payload"]["image"] for item in templates if item["payload"]["template_type"] == "docker"]
        self.assertTrue(all(image.startswith("byot-cps/") for image in docker_images))

    def test_documentation_and_smoke_project_use_byot_cps_name(self):
        readme = (ROOT / "README.md").read_text()
        smoke_test = (ROOT / "src/smoke_test.py").read_text()
        self.assertTrue(readme.startswith("# byot-cps"))
        self.assertIn('name = "byot-cps-smoke-"', smoke_test)

    def test_public_metadata_has_no_developer_home_path(self):
        private_prefix = "/home/" + "yll"
        for relative in ("README.md", "QUICKSTART.md", "Makefile", "provenance.json"):
            self.assertNotIn(private_prefix, (ROOT / relative).read_text(), relative)

    def test_quickstart_requires_an_explicit_private_source_for_refresh(self):
        quickstart = (ROOT / "QUICKSTART.md").read_text()
        self.assertIn(
            "make refresh-spec SOURCE_PROJECT=/path/to/project/project.gns3",
            quickstart,
        )

    def test_topology_uses_role_based_switch_names(self):
        topology = json.loads((ROOT / "topology.json").read_text())
        switch_names = {node["name"] for node in topology["nodes"] if node["node_type"] == "ethernet_switch"}
        self.assertEqual(switch_names, {"WAN-SWITCH", "MGMT-SWITCH", "DMZ-SWITCH", "CPS-SWITCH"})
        endpoint_names = {end["node"] for link in topology["links"] for end in link["nodes"]}
        self.assertFalse({"GRAY-SWITCH", "PURPLE-SWITCH", "RED-SWITCH", "BLUE-SWITCH"} & endpoint_names)
    def test_topology_uses_role_based_node_names(self):
        topology = json.loads((ROOT / "topology.json").read_text())
        names = {node["name"] for node in topology["nodes"]}
        expected = {
            "COMPROMISED-IOT-01", "COMPROMISED-IOT-02", "COMPROMISED-IOT-03",
            "CPS-OPERATOR", "RED-TEAM-HOST", "DMZ-WEB-SERVER", "MGMT-ADMIN",
            "C2-SIMULATOR", "EXTERNAL-CLIENT",
        }
        old = {
            "MIRAI-BOT", "MIRAI-BOT-02", "MIRAI-BOT-03", "PC1", "ExploitPC",
            "WEB-SERVER", "IT-ADMIN", "MIRAI-C2", "EXTERNAL-PC",
        }
        self.assertTrue(expected.issubset(names))
        self.assertFalse(old & names)
        endpoints = {end["node"] for link in topology["links"] for end in link["nodes"]}
        self.assertTrue(expected.issubset(endpoints))
        self.assertFalse(old & endpoints)


if __name__ == "__main__":
    unittest.main()
