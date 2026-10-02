#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

TEMPLATE_KEYS = {
    "bbd7075f-c5e3-4ad0-aea9-478c86e97175": "pfsense",
    "592a288d-be5f-42b5-a1d7-f64bfffd3773": "ubuntu24",
    "77c14d5d-e9b6-4fb8-9804-d5eb57fa084a": "ubuntu18",
    "946d2523-3a32-4db9-aa66-327a22bd0f73": "ubuntu_server",
}
KEEP_NODE = ("name", "node_type", "x", "y", "z", "symbol")
CONTAINER_TEMPLATES = {
    "MIRAI-BOT": "ubuntu18_lab",
    "MIRAI-BOT-02": "ubuntu18_lab",
    "MIRAI-BOT-03": "ubuntu18_lab",
    "MIRAI-C2": "ubuntu18_lab",
    "PC1": "ubuntu24_lab",
    "EXTERNAL-PC": "ubuntu24_lab",
    "IT-ADMIN": "ubuntu24_lab",
    "ExploitPC": "ubuntu24_lab",
    "WEB-SERVER": "ubuntu24_web",
}
SWITCH_NAMES = {
    "GRAY-SWITCH": "WAN-SWITCH",
    "PURPLE-SWITCH": "MGMT-SWITCH",
    "RED-SWITCH": "DMZ-SWITCH",
    "BLUE-SWITCH": "CPS-SWITCH",
}
ROLE_NAMES = {
    "MIRAI-BOT": "COMPROMISED-IOT-01",
    "MIRAI-BOT-02": "COMPROMISED-IOT-02",
    "MIRAI-BOT-03": "COMPROMISED-IOT-03",
    "PC1": "CPS-OPERATOR",
    "ExploitPC": "RED-TEAM-HOST",
    "WEB-SERVER": "DMZ-WEB-SERVER",
    "IT-ADMIN": "MGMT-ADMIN",
    "MIRAI-C2": "C2-SIMULATOR",
    "EXTERNAL-PC": "EXTERNAL-CLIENT",
}
PORTABLE_NAMES = {**SWITCH_NAMES, **ROLE_NAMES}
HOST_ACCESS_NODE = {
    "name": "HOST-ACCESS",
    "node_type": "cloud",
    "x": -330,
    "y": -30,
    "z": 1,
    "symbol": ":/symbols/cloud.svg",
    "properties": {
        "interfaces": [],
        "ports_mapping": [
            {
                "interface": "${MGMT_INTERFACE}",
                "name": "${MGMT_INTERFACE}",
                "port_number": 0,
                "type": "ethernet",
            }
        ],
        "remote_console_host": "",
        "remote_console_http_path": "/",
        "remote_console_port": 23,
        "remote_console_type": "none",
    },
}

def export(source):
    data = json.loads(Path(source).read_text())
    topology = data["topology"]
    id_to_name = {n["node_id"]: PORTABLE_NAMES.get(n["name"], n["name"]) for n in topology["nodes"]}
    nodes = []
    for node in topology["nodes"]:
        out = {key: node.get(key) for key in KEEP_NODE if key in node}
        out["name"] = PORTABLE_NAMES.get(out["name"], out["name"])
        if node["name"] in CONTAINER_TEMPLATES:
            out["node_type"] = "docker"
            out["template"] = CONTAINER_TEMPLATES[node["name"]]
        elif node["node_type"] == "qemu":
            try:
                out["template"] = TEMPLATE_KEYS[node["template_id"]]
            except KeyError as exc:
                raise SystemExit(f"Unknown QEMU template id for {node['name']}: {exc.args[0]}")
        else:
            props = node.get("properties", {})
            if node["node_type"] == "cloud":
                props = dict(props)
                props["interfaces"] = []
                props["ports_mapping"] = [{"interface": "${IOT_INTERFACE}", "name": "${IOT_INTERFACE}", "port_number": 0, "type": "ethernet"}]
            out["properties"] = props
        nodes.append(out)
    links = []
    for link in topology["links"]:
        ends = []
        for end in link["nodes"]:
            ends.append({"node": id_to_name[end["node_id"]], "adapter_number": end["adapter_number"], "port_number": end["port_number"]})
        links.append({"nodes": ends})
    if any(node["name"] == "MGMT-SWITCH" for node in nodes) and not any(
        node["name"] == "HOST-ACCESS" for node in nodes
    ):
        if any(
            endpoint["node"] == "MGMT-SWITCH"
            and endpoint["adapter_number"] == 0
            and endpoint["port_number"] == 2
            for link in links
            for endpoint in link["nodes"]
        ):
            raise SystemExit("MGMT-SWITCH port 2 is already used; cannot inject HOST-ACCESS")
        nodes.append(HOST_ACCESS_NODE)
        links.append(
            {
                "nodes": [
                    {"node": "HOST-ACCESS", "adapter_number": 0, "port_number": 0},
                    {"node": "MGMT-SWITCH", "adapter_number": 0, "port_number": 2},
                ]
            }
        )
    project = {key: data[key] for key in ("scene_height", "scene_width", "show_grid", "show_interface_labels", "show_layers", "snap_to_grid")}
    project["name"] = "byot-cps"
    return {"format": 1, "source_project": data["name"], "project": project, "nodes": nodes, "links": links}

def main():
    parser = argparse.ArgumentParser(description="Convert a GNS3 project file to a portable topology specification")
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(export(args.source), indent=2) + "\n")
    print(args.output)
if __name__ == "__main__":
    main()
