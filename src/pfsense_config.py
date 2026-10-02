#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import struct
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED_INTERFACES = {
    "wan": "em0",
    "lan": "em1",
    "opt1": "em2",
    "opt2": "em3",
}
PUBLIC_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "pfsense-public.xml"
IMAGE_SIZE = 32 * 1024 * 1024
PARTITION_OFFSET = 1024 * 1024
PARTITION_START_SECTOR = PARTITION_OFFSET // 512
FAT_DATE_2000_01_01 = ((2000 - 1980) << 9) | (1 << 5) | 1
DUMMY_ADMIN_USERNAME = "admin"
DUMMY_ADMIN_PASSWORD = "admin"
DUMMY_ADMIN_BCRYPT_HASH = "$2b$12$gqP5oxCfMSSnYRlvOEfngO1sFra5J/.TSYfTx/31h0gMUmgCmVlTO"
PUBLIC_ALLOWED_CHILDREN = {
    ("pfsense",): {
        "version", "system", "interfaces", "dhcpd", "unbound", "nat", "filter",
        "revision",
    },
    ("pfsense", "system"): {
        "hostname", "domain", "timezone", "language", "webgui", "group",
        "user", "nextuid", "nextgid",
    },
    ("pfsense", "system", "webgui"): {"protocol"},
    ("pfsense", "system", "group"): {
        "name", "description", "scope", "gid", "member", "priv",
    },
    ("pfsense", "system", "user"): {
        "name", "descr", "scope", "groupname", "uid", "priv", "bcrypt-hash",
    },
    ("pfsense", "interfaces"): {"wan", "lan", "opt1", "opt2"},
    ("pfsense", "dhcpd"): {"lan", "opt1", "opt2"},
    ("pfsense", "unbound"): {"enable", "active_interface", "outgoing_interface"},
    ("pfsense", "nat"): {"outbound"},
    ("pfsense", "nat", "outbound"): {"mode"},
    ("pfsense", "filter"): {"rule"},
    ("pfsense", "filter", "rule"): {
        "type", "interface", "ipprotocol", "descr", "source", "destination",
    },
    ("pfsense", "filter", "rule", "source"): {"network"},
    ("pfsense", "filter", "rule", "destination"): {"any", "network"},
    ("pfsense", "revision"): {"description", "username"},
}
for _interface in ("wan", "lan", "opt1", "opt2"):
    PUBLIC_ALLOWED_CHILDREN[("pfsense", "interfaces", _interface)] = {
        "enable", "if", "descr", "ipaddr", "subnet", "ipaddrv6",
    }
for _interface in ("lan", "opt1", "opt2"):
    PUBLIC_ALLOWED_CHILDREN[("pfsense", "dhcpd", _interface)] = {"enable", "range"}
    PUBLIC_ALLOWED_CHILDREN[("pfsense", "dhcpd", _interface, "range")] = {"from", "to"}
PUBLIC_REPEATABLE_PATHS = {
    ("pfsense", "system", "group"),
    ("pfsense", "filter", "rule"),
}



class ConfigError(ValueError):
    pass


def _validate_public_config(root):
    def check_schema(element, path):
        if element.attrib:
            raise ConfigError(
                f"public configuration contains forbidden attributes at /{'/'.join(path)}"
            )
        allowed = PUBLIC_ALLOWED_CHILDREN.get(path, set())
        unexpected = sorted({child.tag for child in element if child.tag not in allowed})
        if unexpected:
            raise ConfigError(
                f"public configuration contains forbidden elements at /{'/'.join(path)}: "
                + ", ".join(unexpected)
            )
        for tag in {child.tag for child in element}:
            child_path = path + (tag,)
            if child_path not in PUBLIC_REPEATABLE_PATHS and sum(
                child.tag == tag for child in element
            ) > 1:
                raise ConfigError(
                    f"public configuration contains duplicate element at /{'/'.join(child_path)}"
                )
        for child in element:
            check_schema(child, path + (child.tag,))

    check_schema(root, (root.tag,))
    if "-----BEGIN " in "".join(root.itertext()):
        raise ConfigError("public configuration contains PEM material")
    users = root.findall("./system/user")
    if len(users) != 1:
        raise ConfigError("public configuration must contain exactly one user account")
    administrators = [
        user for user in users
        if user.findtext("uid") == "0" or user.findtext("name") == DUMMY_ADMIN_USERNAME
    ]
    if len(administrators) != 1 or administrators[0].findtext("name") != DUMMY_ADMIN_USERNAME:
        raise ConfigError("public configuration must contain exactly one dummy administrator")
    if administrators[0].findtext("bcrypt-hash") != DUMMY_ADMIN_BCRYPT_HASH:
        raise ConfigError("public configuration must use the dummy administrator password hash")
    unbound = root.find("./unbound")
    if unbound is None or unbound.find("enable") is None:
        raise ConfigError("public configuration must enable the DNS Resolver")
    if unbound.findtext("active_interface") != "lan,opt1,opt2":
        raise ConfigError("public DNS Resolver must listen on lan,opt1,opt2")
    if unbound.findtext("outgoing_interface") != "wan":
        raise ConfigError("public DNS Resolver must use the WAN outgoing interface")
    rules = root.findall("./filter/rule")
    for interface in ("opt1", "opt2"):
        block_indices = [
            index
            for index, rule in enumerate(rules)
            if rule.findtext("type") == "block"
            and rule.findtext("interface") == interface
            and rule.findtext("source/network") == interface
            and rule.findtext("destination/network") == "lan"
        ]
        pass_indices = [
            index
            for index, rule in enumerate(rules)
            if rule.findtext("type") == "pass"
            and rule.findtext("interface") == interface
        ]
        if (
            len(block_indices) != 1
            or not pass_indices
            or block_indices[0] > min(pass_indices)
        ):
            raise ConfigError(
                f"public configuration must enforce {interface} management isolation"
            )


def validate_config(path):
    path = Path(path)
    try:
        mode = path.stat().st_mode & 0o777
    except OSError as exc:
        raise ConfigError(f"cannot read pfSense XML: {exc}") from exc
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ConfigError(f"cannot read pfSense XML: {exc}") from exc
    is_public_config = path.resolve() == PUBLIC_CONFIG_PATH.resolve()
    if is_public_config:
        _validate_public_config(root)
    elif mode & 0o077:
        raise ConfigError(f"unsafe configuration permissions {mode:o}; expected 600 or stricter")
    if root.tag != "pfsense":
        raise ConfigError(f"expected <pfsense> root element, found <{root.tag}>")
    version = root.findtext("version")
    if not version:
        raise ConfigError("configuration has no version")
    interfaces = {
        element.tag: element.findtext("if")
        for element in root.findall("./interfaces/*")
    }
    actual = {name: interfaces.get(name) for name in EXPECTED_INTERFACES}
    if actual != EXPECTED_INTERFACES:
        raise ConfigError(
            f"interface mapping does not match the four-adapter GNS3 template: "
            f"expected {EXPECTED_INTERFACES}, found {actual}"
        )
    return {
        "path": str(path),
        "version": version,
        "interfaces": actual,
        "size": path.stat().st_size,
    }


def render_config_with_dummy_admin(source_path, output_path):
    source_path = Path(source_path)
    output_path = Path(output_path)
    validate_config(source_path)
    root = ET.parse(source_path).getroot()
    admin = next(
        (
            user for user in root.findall("./system/user")
            if user.findtext("uid") == "0" or user.findtext("name") == DUMMY_ADMIN_USERNAME
        ),
        None,
    )
    if admin is None:
        raise ConfigError("configuration has no administrator user")
    name = admin.find("name")
    password_hash = admin.find("bcrypt-hash")
    if name is None or password_hash is None:
        raise ConfigError("administrator user is missing name or bcrypt-hash")
    name.text = DUMMY_ADMIN_USERNAME
    password_hash.text = DUMMY_ADMIN_BCRYPT_HASH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    output_path.chmod(0o600)
    return output_path


def _run(command, *, input_text=None, env=None):
    try:
        return subprocess.run(
            command,
            input=input_text,
            text=True,
            check=True,
            capture_output=True,
            env=env,
        )
    except FileNotFoundError as exc:
        raise ConfigError(f"required command is missing: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise ConfigError(f"command failed ({' '.join(command)}): {detail}") from exc


def _normalize_directory_entries(stream, offset, entry_count):
    child_directories = []
    for index in range(entry_count):
        entry_offset = offset + index * 32
        stream.seek(entry_offset)
        entry = bytearray(stream.read(32))
        if not entry or entry[0] == 0x00:
            break
        if entry[0] == 0xE5 or entry[11] == 0x0F:
            continue
        entry[13] = 0
        entry[14:16] = struct.pack("<H", 0)
        entry[16:18] = struct.pack("<H", FAT_DATE_2000_01_01)
        entry[18:20] = struct.pack("<H", FAT_DATE_2000_01_01)
        entry[22:24] = struct.pack("<H", 0)
        entry[24:26] = struct.pack("<H", FAT_DATE_2000_01_01)
        stream.seek(entry_offset)
        stream.write(entry)
        if entry[11] & 0x10 and entry[0] != ord("."):
            child_directories.append(struct.unpack("<H", entry[26:28])[0])
    return child_directories


def _normalize_fat_timestamps(image_path):
    with Path(image_path).open("r+b") as stream:
        stream.seek(PARTITION_OFFSET)
        boot = stream.read(512)
        bytes_per_sector = struct.unpack("<H", boot[11:13])[0]
        sectors_per_cluster = boot[13]
        reserved_sectors = struct.unpack("<H", boot[14:16])[0]
        fat_count = boot[16]
        root_entries = struct.unpack("<H", boot[17:19])[0]
        sectors_per_fat = struct.unpack("<H", boot[22:24])[0]
        root_offset = PARTITION_OFFSET + (reserved_sectors + fat_count * sectors_per_fat) * bytes_per_sector
        root_sectors = (root_entries * 32 + bytes_per_sector - 1) // bytes_per_sector
        data_offset = root_offset + root_sectors * bytes_per_sector
        children = _normalize_directory_entries(stream, root_offset, root_entries)
        for cluster in children:
            directory_offset = data_offset + (cluster - 2) * sectors_per_cluster * bytes_per_sector
            _normalize_directory_entries(stream, directory_offset, sectors_per_cluster * bytes_per_sector // 32)


def build_config_drive(config_path, output_path):
    config_path = Path(config_path).resolve()
    output_path = Path(output_path).resolve()
    validate_config(config_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=output_path.name + ".", dir=output_path.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    rendered_config = temporary.with_suffix(".xml")
    try:
        render_config_with_dummy_admin(config_path, rendered_config)
        with temporary.open("r+b") as stream:
            stream.truncate(IMAGE_SIZE)
        partition_layout = (
            "label: dos\n"
            "label-id: 0x50465345\n"
            "unit: sectors\n\n"
            f"start={PARTITION_START_SECTOR}, type=c, bootable\n"
        )
        _run(["sfdisk", "--quiet", str(temporary)], input_text=partition_layout)
        _run([
            "mkfs.vfat", "--invariant", "-F", "16", "-n", "PFSENSECFG",
            "--offset", str(PARTITION_START_SECTOR), str(temporary),
        ])
        mtools_env = dict(os.environ)
        mtools_env["MTOOLS_SKIP_CHECK"] = "1"
        image_spec = f"{temporary}@@{PARTITION_OFFSET}"
        _run(["mmd", "-i", image_spec, "::/config"], env=mtools_env)
        _run(["mcopy", "-o", "-i", image_spec, str(rendered_config), "::/config/config.xml"], env=mtools_env)
        _normalize_fat_timestamps(temporary)
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
        rendered_config.unlink(missing_ok=True)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Validate pfSense XML and build FAT configuration media")
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output:
        output = build_config_drive(args.config, args.output)
        result = validate_config(args.config)
        result["image"] = str(output)
    else:
        result = validate_config(args.config)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
