#!/usr/bin/env python3
import copy
import re

COMPROMISED_IOT_PATTERN = re.compile(r"^COMPROMISED-IOT-\d{2,}$")


class CompromisedIoTCountError(ValueError):
    pass


def _is_compromised_iot_name(name):
    return bool(COMPROMISED_IOT_PATTERN.fullmatch(name))


def _compromised_iot_name(number):
    return f"COMPROMISED-IOT-{number:02d}"


def _position(number, existing_positions):
    name = _compromised_iot_name(number)
    if name in existing_positions:
        return existing_positions[name]
    offset = number - 4
    return 120 + 150 * (offset % 5), 345 + 150 * (offset // 5)


def materialize_compromised_iot_count(spec, count):
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise CompromisedIoTCountError("compromised IoT count must be a non-negative integer")

    result = copy.deepcopy(spec)
    source_nodes = [node for node in result["nodes"] if _is_compromised_iot_name(node["name"])]
    if not source_nodes:
        raise CompromisedIoTCountError("topology has no COMPROMISED-IOT prototype")

    prototype = copy.deepcopy(next(
        (node for node in source_nodes if node["name"] == "COMPROMISED-IOT-01"),
        source_nodes[0],
    ))
    existing_positions = {node["name"]: (node["x"], node["y"]) for node in source_nodes}
    result["nodes"] = [node for node in result["nodes"] if not _is_compromised_iot_name(node["name"])]
    result["links"] = [
        link for link in result["links"]
        if not any(_is_compromised_iot_name(endpoint["node"]) for endpoint in link["nodes"])
    ]

    red_team_link = next(
        link for link in result["links"]
        if {endpoint["node"] for endpoint in link["nodes"]} == {"CPS-SWITCH", "RED-TEAM-HOST"}
    )
    cps_red_team_endpoint = next(
        endpoint for endpoint in red_team_link["nodes"] if endpoint["node"] == "CPS-SWITCH"
    )
    cps_red_team_endpoint["adapter_number"] = 0
    cps_red_team_endpoint["port_number"] = 3 + count

    for number in range(1, count + 1):
        name = _compromised_iot_name(number)
        node = copy.deepcopy(prototype)
        node["name"] = name
        node["x"], node["y"] = _position(number, existing_positions)
        result["nodes"].append(node)
        result["links"].append({
            "nodes": [
                {"node": "CPS-SWITCH", "adapter_number": 0, "port_number": number + 2},
                {"node": name, "adapter_number": 0, "port_number": 0},
            ]
        })

    cps_switch = next(node for node in result["nodes"] if node["name"] == "CPS-SWITCH")
    port_count = max(8, count + 4)
    cps_switch["properties"]["ports_mapping"] = [
        {"name": f"Ethernet{number}", "port_number": number, "type": "access", "vlan": 1}
        for number in range(port_count)
    ]

    return result
