#!/usr/bin/env python3
import json
import os
from pathlib import Path

from gns3_api import GNS3API

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QEMU_PATH = "/usr/bin/qemu-system-x86_64"
SERVER_GENERATED_TEMPLATE_FIELDS = {"template_id"}
MISSING = object()


def resolve_declarations(declarations, environment=None):
    environment = os.environ if environment is None else environment
    qemu_path = environment.get("QEMU_PATH", DEFAULT_QEMU_PATH)
    if not qemu_path:
        raise ValueError("QEMU_PATH must not be empty")

    def resolve(value):
        if isinstance(value, str):
            return value.replace("${QEMU_PATH}", qemu_path)
        if isinstance(value, list):
            return [resolve(item) for item in value]
        if isinstance(value, dict):
            return {key: resolve(item) for key, item in value.items()}
        return value

    return resolve(declarations)


def payload_differences(actual, expected):
    differences = {}
    keys = (set(actual) | set(expected)) - SERVER_GENERATED_TEMPLATE_FIELDS
    for key in keys:
        actual_value = actual.get(key, MISSING)
        expected_value = expected.get(key, MISSING)
        if actual_value != expected_value:
            differences[key] = {
                "actual": "<missing>" if actual_value is MISSING else actual_value,
                "expected": "<missing>" if expected_value is MISSING else expected_value,
            }
    return differences


def verify_template(api, template_id, payload):
    actual = api.get(f"/templates/{template_id}")
    differences = payload_differences(actual, payload)
    if differences:
        raise RuntimeError(
            f"GNS3 template {payload['name']!r} does not match declared payload after write: "
            f"{differences}. Remove the stale owned template in GNS3 and rerun "
            "'make templates', or add the field to gns3_templates.json explicitly."
        )
    return actual


def reconcile_templates(api, declarations):
    existing = {item["name"]: item for item in api.get("/templates")}
    counts = {"created": 0, "updated": 0, "unchanged": 0}
    for item in declarations:
        name = item["name"]
        payload = item["payload"]
        current = existing.get(name)
        if current is None:
            result = api.post("/templates", payload)
            template_id = result["template_id"]
            verify_template(api, template_id, payload)
            print("created:", name, template_id)
            counts["created"] += 1
            continue
        template_id = current["template_id"]
        differences = payload_differences(current, payload)
        if differences:
            api.put(f"/templates/{template_id}", payload)
            verify_template(api, template_id, payload)
            print("updated:", name, template_id, sorted(differences))
            counts["updated"] += 1
        else:
            verify_template(api, template_id, payload)
            print("unchanged:", name, template_id)
            counts["unchanged"] += 1
    return counts


def main():
    api = GNS3API()
    print("GNS3", api.get("/version")["version"])
    declarations = resolve_declarations(
        json.loads((ROOT / "gns3_templates.json").read_text())["templates"]
    )
    counts = reconcile_templates(api, declarations)
    print(
        "templates "
        + " ".join(f"{name}={count}" for name, count in counts.items())
    )


if __name__ == "__main__":
    main()
