#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SSH_EXPECTED = {
    "passwordauthentication": "yes",
    "permitrootlogin": "no",
    "usepam": "yes",
}
SUSPICIOUS_EXECUTABLE_MARKERS = ("mirai", "xmrig", "minerd", "kinsing")


def run(command, **kwargs):
    return subprocess.run(command, text=True, capture_output=True, **kwargs)


def docker_exec(container, command, user=None, input_text=None, check=True):
    invocation = ["docker", "exec"]
    if input_text is not None:
        invocation.append("-i")
    if user:
        invocation.extend(["--user", user])
    invocation.extend([container, *command])
    result = run(invocation, input=input_text)
    if check and result.returncode:
        raise RuntimeError(
            f"container command failed ({result.returncode}): {' '.join(command)}: "
            f"{result.stderr.strip()}"
        )
    return result


def validate_probe(declaration, probe):
    errors = []
    if probe["ubuntu_version"] != declaration["ubuntu_version"]:
        errors.append(
            f"Ubuntu version {probe['ubuntu_version']!r}, expected {declaration['ubuntu_version']!r}"
        )
    if probe["pid1_user"] != declaration["default_user"]:
        errors.append(
            f"default process user {probe['pid1_user']!r}, expected {declaration['default_user']!r}"
        )
    if declaration["required_group"] not in probe["groups"]:
        errors.append(f"missing required group: {declaration['required_group']}")
    if probe["sudo_without_password"]:
        errors.append("sudo accepted a command without a password")
    if not probe["sudo_with_password"]:
        errors.append("sudo rejected the documented lab password")
    for key, expected in SSH_EXPECTED.items():
        if probe["ssh"].get(key) != expected:
            errors.append(f"SSH {key}={probe['ssh'].get(key)!r}, expected {expected!r}")
    missing_tools = [name for name in declaration["required_tools"] if not probe["tools"].get(name)]
    if missing_tools:
        errors.append(f"missing required tools: {missing_tools}")
    unexpected_listeners = sorted(set(probe["listeners"]) - set(declaration["allowed_listeners"]))
    if unexpected_listeners:
        errors.append(f"unexpected listener(s): {unexpected_listeners}")
    missing_listeners = sorted(
        set(declaration.get("required_listeners", [])) - set(probe["listeners"])
    )
    if missing_listeners:
        errors.append(f"missing required listener(s): {missing_listeners}")
    unexpected_processes = sorted(set(probe["processes"]) - set(declaration["allowed_processes"]))
    if unexpected_processes:
        errors.append(f"unexpected service process(es): {unexpected_processes}")
    missing_processes = sorted(
        set(declaration.get("required_processes", [])) - set(probe["processes"])
    )
    if missing_processes:
        errors.append(f"missing required process(es): {missing_processes}")
    expected_http = declaration.get("http_body_contains")
    if expected_http and expected_http not in probe.get("http_body", ""):
        errors.append(f"HTTP response is missing expected text: {expected_http!r}")
    if probe["suspicious_files"]:
        errors.append(f"suspicious executable name(s): {probe['suspicious_files']}")
    return errors


def collect_probe(declaration):
    container = "byot-cps-runtime-" + uuid.uuid4().hex[:12]
    created = False
    try:
        result = run(["docker", "run", "-d", "--rm", "--name", container, declaration["image"]])
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        created = True
        for _ in range(30):
            ready = docker_exec(container, ["sh", "-c", "ss -H -lnt | grep -q ':22 '"], check=False)
            if ready.returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("SSH did not start within six seconds")

        os_release = docker_exec(container, ["cat", "/etc/os-release"]).stdout
        version_match = re.search(r'^VERSION_ID="?([^"\n]+)"?$', os_release, re.MULTILINE)
        if not version_match:
            raise RuntimeError("VERSION_ID is missing from /etc/os-release")

        uid = docker_exec(
            container,
            ["sh", "-c", "awk '/^Uid:/ {print $2}' /proc/1/status"],
        ).stdout.strip()
        pid1_user = docker_exec(
            container,
            ["sh", "-c", f"getent passwd {uid} | cut -d: -f1"],
        ).stdout.strip()
        groups = docker_exec(container, ["id", "-nG", declaration["default_user"]]).stdout.split()

        without_password = docker_exec(
            container,
            ["sudo", "-n", "true"],
            user=declaration["default_user"],
            check=False,
        ).returncode == 0
        with_password = docker_exec(
            container,
            ["sudo", "-S", "-p", "", "true"],
            user=declaration["default_user"],
            input_text="lab\n",
            check=False,
        ).returncode == 0

        ssh_output = docker_exec(container, ["sshd", "-T"]).stdout
        ssh = {}
        for line in ssh_output.splitlines():
            fields = line.split(None, 1)
            if len(fields) == 2 and fields[0] in SSH_EXPECTED:
                ssh[fields[0]] = fields[1]

        tools = {
            name: docker_exec(
                container,
                ["sh", "-c", f"command -v {name} >/dev/null"],
                check=False,
            ).returncode
            == 0
            for name in declaration["required_tools"]
        }

        http_body = ""
        if declaration.get("http_body_contains"):
            http_body = docker_exec(
                container,
                ["curl", "--fail", "--silent", "--show-error", "http://127.0.0.1/"],
            ).stdout

        listeners = set()
        for line in docker_exec(container, ["ss", "-H", "-lntu"]).stdout.splitlines():
            fields = line.split()
            if len(fields) < 5:
                continue
            protocol = fields[0].lower()
            port_match = re.search(r":(\d+)$", fields[4])
            if port_match:
                listeners.add(f"{protocol}:{port_match.group(1)}")

        top = run(["docker", "top", container, "-eo", "pid,user,comm"], check=True).stdout
        processes = [line.split()[-1] for line in top.splitlines()[1:] if line.split()]

        executable_names = docker_exec(
            container,
            [
                "find",
                "/bin",
                "/sbin",
                "/usr/bin",
                "/usr/sbin",
                "/usr/local/bin",
                "-xdev",
                "-type",
                "f",
                "-printf",
                "%f\\n",
            ],
        ).stdout.splitlines()
        suspicious = sorted(
            name
            for name in executable_names
            if any(marker in name.lower() for marker in SUSPICIOUS_EXECUTABLE_MARKERS)
        )

        return {
            "ubuntu_version": version_match.group(1),
            "pid1_user": pid1_user,
            "groups": groups,
            "sudo_without_password": without_password,
            "sudo_with_password": with_password,
            "ssh": ssh,
            "tools": tools,
            "http_body": http_body,
            "listeners": sorted(listeners),
            "processes": sorted(processes),
            "suspicious_files": suspicious,
        }
    finally:
        if created:
            run(["docker", "rm", "-f", container])


def main():
    parser = argparse.ArgumentParser(description="Runtime-test both BYOT-CPS lab container images")
    parser.add_argument("--manifest", type=Path, default=ROOT / "container_images.json")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    failed = False
    for declaration in manifest["images"]:
        try:
            probe = collect_probe(declaration)
            errors = validate_probe(declaration, probe)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
            errors = [str(exc)]
            probe = None
        if errors:
            failed = True
            print("FAIL", declaration["image"])
            for error in errors:
                print(" -", error)
            if probe:
                print(json.dumps(probe, indent=2, sort_keys=True))
        else:
            print("OK", declaration["image"], json.dumps(probe, sort_keys=True))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
