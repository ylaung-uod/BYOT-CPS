#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from gns3_api import GNS3API
from gns3_cleanup import delete_project_and_confirm
from topology_transform import materialize_compromised_iot_count

ROOT = Path(__file__).resolve().parents[1]

def resolve(value):
    if isinstance(value, str):
        return value.replace("${IOT_INTERFACE}", os.environ.get("IOT_INTERFACE", "docker0"))
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
