#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from gns3_api import GNS3API
from gns3_cleanup import delete_project_and_confirm
from topology_transform import materialize_compromised_iot_count

ROOT = Path(__file__).resolve().parents[1]


def host_access_matches(nodes, links, interface):
    host_nodes = [node for node in nodes if node.get("name") == "HOST-ACCESS"]
    management_nodes = [node for node in nodes if node.get("name") == "MGMT-SWITCH"]
    if len(host_nodes) != 1 or len(management_nodes) != 1:
        return False
    host_access = host_nodes[0]
    management_switch = management_nodes[0]
    mappings = host_access.get("properties", {}).get("ports_mapping", [])
    if len(mappings) != 1:
        return False
    mapping = mappings[0]
    if not (
        mapping.get("interface") == interface
        and mapping.get("name") == interface
        and mapping.get("port_number") == 0
        and mapping.get("type") == "ethernet"
    ):
        return False
    host_id = host_access.get("node_id")
    management_id = management_switch.get("node_id")
    host_links = [
        link for link in links
        if any(endpoint.get("node_id") == host_id for endpoint in link.get("nodes", []))
    ]
    if len(host_links) != 1:
        return False
    endpoints = {
        (
            endpoint.get("node_id"),
            endpoint.get("adapter_number"),
            endpoint.get("port_number"),
        )
        for endpoint in host_links[0].get("nodes", [])
    }
    return endpoints == {
        (host_id, 0, 0),
        (management_id, 0, 2),
    }


def resolve(value):
    if isinstance(value, str):
        return (
            value.replace("${IOT_INTERFACE}", os.environ.get("IOT_INTERFACE", "docker0"))
            .replace("${MGMT_INTERFACE}", os.environ.get("MGMT_INTERFACE", "byot-mgmt"))
        )
    if isinstance(value, list):
        return [resolve(v) for v in value]
    if isinstance(value, dict):
        return {k: resolve(v) for k, v in value.items()}
    return value

def build(api, name, compromised_iot_count=3):
    spec = materialize_compromised_iot_count(resolve(json.loads((ROOT / "topology.json").read_text())), compromised_iot_count)
    projects = api.get("/projects")
    if any(p["name"] == name for p in projects):
        raise SystemExit(f"Project {name!r} already exists; refusing to modify it")
    project_payload = dict(spec["project"])
    project_payload["name"] = name
    project = api.post("/projects", project_payload)
    pid = project["project_id"]
    try:
        api.post(f"/projects/{pid}/open")
        template_names = {x["key"]: x["name"] for x in json.loads((ROOT / "gns3_templates.json").read_text())["templates"]}
        templates = {x["name"]: x["template_id"] for x in api.get("/templates")}
        node_ids = {}
        for node in spec["nodes"]:
            if "template" in node:
                wanted = template_names[node["template"]]
                if wanted not in templates:
                    raise RuntimeError(f"Missing GNS3 template: {wanted}; run make templates")
                made = api.post(f"/projects/{pid}/templates/{templates[wanted]}", {"x": node["x"], "y": node["y"]})
                made = api.put(f"/projects/{pid}/nodes/{made['node_id']}", {"name": node["name"], "x": node["x"], "y": node["y"]})
            else:
                payload = {k: node[k] for k in ("name", "node_type", "x", "y", "z", "symbol", "properties") if k in node}
                payload["compute_id"] = "local"
                made = api.post(f"/projects/{pid}/nodes", payload)
            node_ids[node["name"]] = made["node_id"]
            print("node:", node["name"])
        for link in spec["links"]:
            payload = {"nodes": []}
            for end in link["nodes"]:
                payload["nodes"].append({"node_id": node_ids[end["node"]], "adapter_number": end["adapter_number"], "port_number": end["port_number"]})
            api.post(f"/projects/{pid}/links", payload)
        print(f"created project {name!r}: {len(node_ids)} nodes, {len(spec['links'])} links, id={pid}")
        return pid
    except Exception:
        delete_project_and_confirm(api, pid, name)
        raise

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-name", default="byot-cps")
    parser.add_argument("--compromised-iot-count", type=int, default=3)
    args = parser.parse_args()
    build(GNS3API(), args.project_name, args.compromised_iot_count)
if __name__ == "__main__":
    main()
