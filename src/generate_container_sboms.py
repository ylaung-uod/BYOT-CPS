#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def spdx_id(prefix, value):
    digest = hashlib.sha256(value.encode()).hexdigest()[:16]
    return f"SPDXRef-{prefix}-{digest}"


def snapshot_created(snapshot):
    match = re.fullmatch(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z", snapshot)
    if not match:
        raise ValueError(f"invalid Ubuntu snapshot timestamp: {snapshot}")
    year, month, day, hour, minute, second = match.groups()
    return f"{year}-{month}-{day}T{hour}:{minute}:{second}Z"


def build_spdx_document(declaration, packages):
    packages = sorted(packages, key=lambda item: (item[0], item[1], item[2]))
    identity = json.dumps(
        {"declaration": declaration, "packages": packages},
        sort_keys=True,
        separators=(",", ":"),
    )
    namespace_digest = hashlib.sha256(identity.encode()).hexdigest()
    image_id = spdx_id("ContainerImage", declaration["image"])
    package_entries = [
        {
            "SPDXID": image_id,
            "name": declaration["key"],
            "versionInfo": declaration["snapshot"],
            "sourceInfo": f"Base image: {declaration['base']}@{declaration['base_digest']}",
            "downloadLocation": "NOASSERTION",
            "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION",
            "licenseDeclared": "NOASSERTION",
            "copyrightText": "NOASSERTION",
            "externalRefs": [
                {
                    "referenceCategory": "OTHER",
                    "referenceType": "docker-image",
                    "referenceLocator": declaration["image"],
                }
            ],
        }
    ]
    relationships = []
    for name, version, architecture in packages:
        package_id = spdx_id("DebPackage", f"{name}\0{version}\0{architecture}")
        package_entries.append(
            {
                "SPDXID": package_id,
                "name": name,
                "versionInfo": version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
                "comment": f"Architecture: {architecture}",
            }
        )
        relationships.append(
            {
                "spdxElementId": image_id,
                "relationshipType": "CONTAINS",
                "relatedSpdxElement": package_id,
            }
        )
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"BYOT-CPS {declaration['key']} container SBOM",
        "documentNamespace": f"https://byot-cps.invalid/spdx/{declaration['key']}/{namespace_digest}",
        "creationInfo": {
            "created": snapshot_created(declaration["snapshot"]),
            "creators": ["Tool: byot-cps/generate_container_sboms.py"],
        },
        "documentDescribes": [image_id],
        "packages": package_entries,
        "relationships": relationships,
    }


def installed_packages(image):
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "dpkg-query",
            image,
            "-W",
            "-f=${binary:Package}\\t${Version}\\t${Architecture}\\n",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    packages = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) != 3 or not all(fields):
            raise RuntimeError(f"unexpected dpkg-query output: {line!r}")
        packages.append(tuple(fields))
    return packages


def generate(manifest_path, check=False):
    manifest = json.loads(Path(manifest_path).read_text())
    for declaration in manifest["images"]:
        document = build_spdx_document(
            declaration,
            installed_packages(declaration["image"]),
        )
        destination = ROOT / declaration["sbom"]
        rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
        if check:
            if not destination.is_file() or destination.read_text() != rendered:
                raise RuntimeError(f"stale container SBOM: {destination}")
            print("OK", destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(rendered)
            print("wrote", destination)


def main():
    parser = argparse.ArgumentParser(description="Generate deterministic SPDX SBOMs from built lab containers")
    parser.add_argument("--manifest", type=Path, default=ROOT / "container_images.json")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generate(args.manifest, args.check)


if __name__ == "__main__":
    main()
