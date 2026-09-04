import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from topology_transform import CompromisedIoTCountError, materialize_compromised_iot_count


class ConfigurableCompromisedIoTCountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((ROOT / "topology.json").read_text())

    def node_names(self, spec):
        return sorted(node["name"] for node in spec["nodes"] if node["name"].startswith("COMPROMISED-IOT-"))

    def cps_port_for(self, spec, node_name):
        for link in spec["links"]:
            names = {end["node"] for end in link["nodes"]}
            if names == {"CPS-SWITCH", node_name}:
                return next(end["port_number"] for end in link["nodes"] if end["node"] == "CPS-SWITCH")
        self.fail(f"no CPS-SWITCH link for {node_name}")

    def test_zero_nodes_removes_all_compromised_iot_nodes_and_links(self):
        result = materialize_compromised_iot_count(self.spec, 0)
        self.assertEqual(self.node_names(result), [])
        self.assertEqual(self.cps_port_for(result, "RED-TEAM-HOST"), 3)
        self.assertEqual(len(result["nodes"]), 13)
        self.assertEqual(len(result["links"]), 12)

    def test_one_node_uses_01_suffix(self):
        result = materialize_compromised_iot_count(self.spec, 1)
        self.assertEqual(self.node_names(result), ["COMPROMISED-IOT-01"])
        self.assertEqual(self.cps_port_for(result, "COMPROMISED-IOT-01"), 3)
        self.assertEqual(self.cps_port_for(result, "RED-TEAM-HOST"), 4)

    def test_five_nodes_have_stable_names_and_unique_switch_ports(self):
        result = materialize_compromised_iot_count(self.spec, 5)
        self.assertEqual(self.node_names(result), [
            "COMPROMISED-IOT-01", "COMPROMISED-IOT-02", "COMPROMISED-IOT-03",
            "COMPROMISED-IOT-04", "COMPROMISED-IOT-05",
        ])
        self.assertEqual([self.cps_port_for(result, name) for name in self.node_names(result)], [3, 4, 5, 6, 7])
        self.assertEqual(self.cps_port_for(result, "RED-TEAM-HOST"), 8)
        cps = next(node for node in result["nodes"] if node["name"] == "CPS-SWITCH")
        mapped_ports = {entry["port_number"] for entry in cps["properties"]["ports_mapping"]}
        self.assertTrue(set(range(9)).issubset(mapped_ports))

    def test_materialization_does_not_modify_source_spec(self):
        before = json.dumps(self.spec, sort_keys=True)
        materialize_compromised_iot_count(self.spec, 5)
        self.assertEqual(json.dumps(self.spec, sort_keys=True), before)

    def test_negative_or_non_integer_count_is_rejected(self):
        for value in (-1, 1.5, "3", True):
            with self.subTest(value=value):
                with self.assertRaises(CompromisedIoTCountError):
                    materialize_compromised_iot_count(self.spec, value)

    def test_makefile_and_cli_expose_compromised_iot_count(self):
        makefile = (ROOT / "Makefile").read_text()
        builder = (ROOT / "src/create_topology.py").read_text()
        self.assertIn("COMPROMISED_IOT_COUNT ?= 3", makefile)
        self.assertIn("--compromised-iot-count", builder)
        self.assertIn("$(COMPROMISED_IOT_COUNT)", makefile)


if __name__ == "__main__":
    unittest.main()
