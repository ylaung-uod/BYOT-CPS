#!/usr/bin/env python3
import argparse
import gzip
import hashlib
import io
import os
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.0.0"
ARCHIVE_ROOT = f"byot-cps-v{VERSION}"

SOURCE_FILES = {
    "CITATION.cff": "CITATION.cff",
    "Dockerfiles/ubuntu18-lab/Dockerfile": "Dockerfiles/ubuntu18-lab/Dockerfile",
    "Dockerfiles/ubuntu18-lab/entrypoint.sh": "Dockerfiles/ubuntu18-lab/entrypoint.sh",
    "Dockerfiles/ubuntu18-lab/isrg-root-x1.pem": "Dockerfiles/ubuntu18-lab/isrg-root-x1.pem",
    "Dockerfiles/ubuntu24-lab/Dockerfile": "Dockerfiles/ubuntu24-lab/Dockerfile",
    "Dockerfiles/ubuntu24-lab/entrypoint.sh": "Dockerfiles/ubuntu24-lab/entrypoint.sh",
    "Dockerfiles/ubuntu24-lab/isrg-root-x1.pem": "Dockerfiles/ubuntu24-lab/isrg-root-x1.pem",
    "LICENSE": "LICENSE",
    "packaging/reproduction/Makefile": "Makefile",
    "NOTICE.md": "NOTICE.md",
    "QUICKSTART.md": "QUICKSTART.md",
    "REPRODUCTION.md": "README.md",
    "SECURITY.md": "SECURITY.md",
    "config/pfsense-public.xml": "config/pfsense-public.xml",
    "container_images.json": "container_images.json",
    "docs/ARCHITECTURE.md": "docs/ARCHITECTURE.md",
    "docs/ARTIFACTS.md": "docs/ARTIFACTS.md",
    "docs/CONTAINERS.md": "docs/CONTAINERS.md",
    "docs/REPRODUCIBILITY.md": "docs/REPRODUCIBILITY.md",
    "docs/SECURITY-BOUNDARY.md": "docs/SECURITY-BOUNDARY.md",
    "gns3_templates.json": "gns3_templates.json",
    "images.json": "images.json",
    "images/README.md": "images/README.md",
    "pfsense/README.md": "pfsense/README.md",
    "provenance.json": "provenance.json",
    "requirements.txt": "requirements.txt",
    "sbom/ubuntu18-lab.spdx.json": "sbom/ubuntu18-lab.spdx.json",
    "sbom/ubuntu24-lab.spdx.json": "sbom/ubuntu24-lab.spdx.json",
    "src/create_templates.py": "src/create_templates.py",
    "src/create_topology.py": "src/create_topology.py",
    "src/fetch_help.py": "src/fetch_help.py",
    "src/generate_container_sboms.py": "src/generate_container_sboms.py",
    "src/gns3_api.py": "src/gns3_api.py",
    "src/gns3_cleanup.py": "src/gns3_cleanup.py",
    "src/pfsense_config.py": "src/pfsense_config.py",
    "src/prepare_images.py": "src/prepare_images.py",
    "src/smoke_test.py": "src/smoke_test.py",
    "src/test_container_images.py": "src/test_container_images.py",
    "src/topology_transform.py": "src/topology_transform.py",
    "src/validate.py": "src/validate.py",
    "src/verify_images.py": "src/verify_images.py",
    "topology.json": "topology.json",
}


def normalized_info(name, data, executable=False):
    info = tarfile.TarInfo(f"{ARCHIVE_ROOT}/{name}")
    info.size = len(data)
    info.mode = 0o755 if executable else 0o644
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def collect_files():
    files = {}
    for source_name, archive_name in SOURCE_FILES.items():
        archive_path = PurePosixPath(archive_name)
        if (
            archive_path.is_absolute()
            or ".." in archive_path.parts
            or not archive_path.parts
            or archive_name in files
        ):
            raise ValueError(f"unsafe or duplicate archive path: {archive_name!r}")
        source = ROOT / source_name
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"required regular source file is missing: {source_name}")
        data = source.read_bytes()
        executable = bool(source.stat().st_mode & stat.S_IXUSR)
        files[archive_name] = (data, executable)
    manifest = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n"
        for name, (data, _) in sorted(files.items())
    ).encode()
    files["REPRODUCTION-MANIFEST.sha256"] = (manifest, False)
    return files


def build_archive(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    files = collect_files()
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=output.name + ".", dir=output.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(
                    fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
                ) as archive:
                    for name, (data, executable) in sorted(files.items()):
                        archive.addfile(
                            normalized_info(name, data, executable), io.BytesIO(data)
                        )
        os.chmod(temporary, 0o644)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"created: {output} ({len(files)} files)")


def main():
    parser = argparse.ArgumentParser(
        description="Build the minimal deterministic BYOT-CPS reproduction archive"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / f"byot-cps-v{VERSION}-reproduction.tar.gz",
    )
    args = parser.parse_args()
    try:
        build_archive(args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
