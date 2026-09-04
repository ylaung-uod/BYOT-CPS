#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from prepare_images import ArtifactError, file_digest, verify_blank_disk, verify_regular_file

ROOT = Path(__file__).resolve().parents[1]


def verify_images(manifest, image_dir, qemu_img="qemu-img"):
    if manifest.get("algorithm") != "sha256":
        raise ArtifactError("images manifest must use sha256")
    image_dir = Path(image_dir)
    results = []
    for declaration in manifest["images"]:
        path = image_dir / declaration["name"]
        if not path.is_file():
            raise ArtifactError(f"missing artifact: {path}")
        if declaration["source"] == "generated":
            verify_blank_disk(path, declaration, qemu_img)
            results.append(
                f"OK {declaration['name']} format={declaration['format']} "
                f"virtual_size={declaration['virtual_size']}"
            )
        elif declaration["source"] == "vendor-download":
            verify_regular_file(path, declaration)
            digest, size = file_digest(path)
            results.append(f"OK {declaration['name']} sha256={digest} size={size}")
        else:
            raise ArtifactError(
                f"unsupported artifact source: {declaration['source']}"
            )
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Verify generated and vendor-supplied GNS3 image artifacts"
    )
    parser.add_argument("--manifest", type=Path, default=ROOT / "images.json")
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path(os.environ.get("GNS3_QEMU_IMAGES", "~/GNS3/images/QEMU")).expanduser(),
    )
    args = parser.parse_args()
    try:
        results = verify_images(
            json.loads(args.manifest.read_text()),
            args.image_dir,
        )
    except (ArtifactError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    for result in results:
        print(result)


if __name__ == "__main__":
    main()
