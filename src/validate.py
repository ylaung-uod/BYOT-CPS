#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
spec = json.loads((ROOT / "topology.json").read_text())
templates = json.loads((ROOT / "gns3_templates.json").read_text())["templates"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


require(spec["format"] == 1, f"unsupported topology format: {spec['format']!r}")
names = [n["name"] for n in spec["nodes"]]
require(len(names) == len(set(names)), "duplicate node names")
known = set(names)
used_ports = set()
for index, link in enumerate(spec["links"], 1):
    require(len(link["nodes"]) == 2, f"link {index} does not have two endpoints")
    for end in link["nodes"]:
        require(end["node"] in known, f"link {index} references unknown node")
        port = (end["node"], end["adapter_number"], end["port_number"])
        require(port not in used_ports, f"port used twice: {port}")
        used_ports.add(port)
keys = {t["key"] for t in templates}
for node in spec["nodes"]:
    if "template" in node:
        require(
            node["template"] in keys,
            f"node {node['name']!r} references unknown template {node['template']!r}",
        )
counts = Counter(n["node_type"] for n in spec["nodes"])
require(len(spec["nodes"]) == 16, f"expected 16 nodes, found {len(spec['nodes'])}")
require(len(spec["links"]) == 15, f"expected 15 links, found {len(spec['links'])}")
expected_counts = {"cloud": 1, "docker": 9, "ethernet_switch": 4, "nat": 1, "qemu": 1}
require(counts == expected_counts, f"unexpected node type counts: {counts}")
print("valid:", len(spec["nodes"]), "nodes,", len(spec["links"]), "links,", dict(sorted(counts.items())))
