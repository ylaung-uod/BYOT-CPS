#!/usr/bin/env python3
import os
import uuid
import time
from collections import Counter
from gns3_api import GNS3API
from gns3_cleanup import delete_project_and_confirm
from create_topology import build


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


api = GNS3API()
name = "byot-cps-smoke-" + uuid.uuid4().hex[:8]
compromised_iot_count = int(os.environ.get("COMPROMISED_IOT_COUNT", "3"))
pid = build(api, name, compromised_iot_count)
try:
    remote = api.get(f"/projects/{pid}")
    nodes = api.get(f"/projects/{pid}/nodes")
    links = api.get(f"/projects/{pid}/links")
    require(
        len(nodes) == 13 + compromised_iot_count
        and len(links) == 12 + compromised_iot_count,
        f"unexpected topology size: nodes={len(nodes)} links={len(links)}",
    )
    counts = Counter(node["node_type"] for node in nodes)
    expected_counts = {
        "cloud": 1,
        "docker": 6 + compromised_iot_count,
        "ethernet_switch": 4,
        "nat": 1,
        "qemu": 1,
    }
    require(counts == expected_counts, f"unexpected node type counts: {counts}")
    firewall = next(node for node in nodes if node["name"] == "FIREWALL")
    require(
        firewall["properties"]["hdb_disk_image"] == "pfsense-config.img",
        f"unexpected firewall properties: {firewall['properties']}",
    )
    api.post(f"/projects/{pid}/nodes/{firewall['node_id']}/start")
    for node in nodes:
        if node["node_type"] == "docker":
            api.post(f"/projects/{pid}/nodes/{node['node_id']}/start")
    time.sleep(5)
    running = api.get(f"/projects/{pid}/nodes")
    docker_statuses = {node["name"]: node["status"] for node in running if node["node_type"] == "docker"}
    require(
        set(docker_statuses.values()) == {"started"},
        f"unexpected Docker node statuses: {docker_statuses}",
    )
    firewall_status = next(node["status"] for node in running if node["name"] == "FIREWALL")
    require(
        firewall_status == "started",
        f"unexpected firewall status: {firewall_status}",
    )
finally:
    delete_project_and_confirm(api, pid, name)
print("smoke test passed and temporary project deleted:", remote["name"])
