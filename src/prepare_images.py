#!/usr/bin/env python3
import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArtifactError(RuntimeError):
    pass


def file_digest(path):
    hasher = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            hasher.update(chunk)
            size += len(chunk)
    return hasher.hexdigest(), size


def verify_regular_file(path, declaration):
    digest, size = file_digest(path)
    if size != declaration["size"] or digest != declaration["sha256"]:
        raise ArtifactError(
            f"artifact mismatch for {path}: sha256={digest} size={size}; "
            f"expected sha256={declaration['sha256']} size={declaration['size']}"
        )


def verify_blank_disk(path, declaration, qemu_img="qemu-img"):
    try:
        result = subprocess.run(
            [qemu_img, "info", "--output=json", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ArtifactError(f"required command is missing: {qemu_img}") from exc
    except subprocess.CalledProcessError as exc:
        raise ArtifactError(f"cannot inspect {path}: {exc.stderr.strip()}") from exc
    info = json.loads(result.stdout)
    if info.get("format") != declaration["format"]:
        raise ArtifactError(
            f"wrong image format for {path}: {info.get('format')}; "
            f"expected {declaration['format']}"
        )
    if info.get("backing-filename") or info.get("full-backing-filename"):
        raise ArtifactError(f"generated disk must not have a backing file: {path}")
    if info.get("virtual-size") != declaration["virtual_size"]:
        raise ArtifactError(
            f"wrong virtual size for {path}: {info.get('virtual-size')}; "
            f"expected {declaration['virtual_size']}"
        )
    try:
        result = subprocess.run(
            [qemu_img, "map", "--output=json", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ArtifactError(f"cannot map {path}: {exc.stderr.strip()}") from exc
    extents = json.loads(result.stdout)
    if any(extent.get("data") for extent in extents):
        raise ArtifactError(f"generated disk is not blank: {path}")


def create_blank_disk(path, declaration, qemu_img="qemu-img"):
    path = Path(path)
    if path.exists():
        verify_blank_disk(path, declaration, qemu_img)
        print("exists:", path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    temporary.unlink()
    try:
        subprocess.run(
            [
                qemu_img,
                "create",
                "-f",
                declaration["format"],
                str(temporary),
                declaration["create_size"],
            ],
            check=True,
        )
        verify_blank_disk(temporary, declaration, qemu_img)
        os.replace(temporary, path)
    except FileNotFoundError as exc:
        raise ArtifactError(f"required command is missing: {qemu_img}") from exc
    except subprocess.CalledProcessError as exc:
        raise ArtifactError(f"failed to create {path}: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)
    print("created:", path)


def install_from_archive(destination, declaration, archive_path):
    destination = Path(destination)
    if destination.exists():
        try:
            verify_regular_file(destination, declaration)
        except ArtifactError:
            pass
        else:
            print("exists:", destination)
            return

    archive_path = Path(archive_path)
    if not archive_path.is_file():
        raise ArtifactError(
            f"missing installer archive: {archive_path}; run 'make fetch-help'"
        )
    verify_regular_file(archive_path, declaration["archive"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=destination.name + ".", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with gzip.open(archive_path, "rb") as source, temporary.open("wb") as target:
            shutil.copyfileobj(source, target, length=8 * 1024 * 1024)
        verify_regular_file(temporary, declaration)
        os.replace(temporary, destination)
    except (gzip.BadGzipFile, EOFError, OSError) as exc:
        raise ArtifactError(f"cannot decompress {archive_path}: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)
    print("installed:", destination)


def prepare_images(manifest, image_dir, archive_path, qemu_img="qemu-img"):
    if manifest.get("algorithm") != "sha256":
        raise ArtifactError("images manifest must use sha256")
    image_dir = Path(image_dir)
    for declaration in manifest["images"]:
        destination = image_dir / declaration["name"]
        source = declaration["source"]
        if source == "generated":
            create_blank_disk(destination, declaration, qemu_img)
        elif source == "vendor-download":
            install_from_archive(destination, declaration, archive_path)
        else:
            raise ArtifactError(f"unsupported artifact source: {source}")


def main():
    parser = argparse.ArgumentParser(
        description="Create the blank pfSense disk and install a verified Netgate ISO"
    )
    parser.add_argument("--manifest", type=Path, default=ROOT / "images.json")
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=Path(os.environ.get("GNS3_QEMU_IMAGES", "~/GNS3/images/QEMU")).expanduser(),
    )
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    installer = next(
        item for item in manifest["images"] if item["source"] == "vendor-download"
    )
    archive = args.archive or Path("downloads") / installer["archive"]["name"]
    try:
        prepare_images(manifest, args.image_dir, archive)
    except (ArtifactError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
