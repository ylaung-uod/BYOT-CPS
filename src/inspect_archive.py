#!/usr/bin/env python3
import argparse
import re
import sys
import tarfile
from pathlib import PurePosixPath

FORBIDDEN_DIRECTORIES = {
    ".git",
    ".state",
    "artifacts",
    "downloads",
    "project-files",
    "secrets",
}
FORBIDDEN_SUFFIXES = {
    ".7z",
    ".der",
    ".gz",
    ".img",
    ".iso",
    ".jks",
    ".kdb",
    ".kdbx",
    ".key",
    ".keystore",
    ".log",
    ".p12",
    ".p8",
    ".pcap",
    ".pcapng",
    ".pfx",
    ".pk8",
    ".pkcs12",
    ".pkcs8",
    ".ppk",
    ".qcow2",
    ".tar",
    ".vmdk",
    ".zip",
}
FORBIDDEN_FILENAMES = {
    ".env",
    "credentials",
    "credentials.json",
    "gns3_server.conf",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
PRIVATE_CONTENT_PATTERNS = (
    re.compile(rb"/home/[A-Za-z0-9._-]+/"),
    re.compile(rb"/Users/[A-Za-z0-9._-]+/"),
    re.compile(rb"[A-Z]:\\Users\\[^\r\n]+", re.IGNORECASE),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(
        rb"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----.*?"
        rb"-----END (?:[A-Z0-9]+ )*PRIVATE KEY-----",
        re.DOTALL,
    ),
    re.compile(
        rb"-----BEGIN PGP PRIVATE "
        rb"KEY BLOCK-----.*?"
        rb"-----END PGP PRIVATE "
        rb"KEY BLOCK-----",
        re.DOTALL,
    ),
)
MAX_MEMBER_SIZE = 10 * 1024 * 1024


class ArchivePolicyError(ValueError):
    pass


def validate_name(name):
    if "\\" in name:
        raise ArchivePolicyError(f"forbidden archive member path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ArchivePolicyError(f"forbidden archive member path: {name!r}")
    lower_parts = tuple(part.lower() for part in path.parts)
    if any(part in FORBIDDEN_DIRECTORIES for part in lower_parts):
        raise ArchivePolicyError(f"forbidden archive member directory: {name!r}")
    lower_path = path.as_posix().lower()
    if lower_parts[0] == "images" and lower_path not in {
        "images",
        "images/readme.md",
    }:
        raise ArchivePolicyError(f"forbidden archive member under images/: {name!r}")
    if path.name.lower() in FORBIDDEN_FILENAMES:
        raise ArchivePolicyError(f"forbidden archive member filename: {name!r}")
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        raise ArchivePolicyError(f"forbidden archive member type: {name!r}")
    return path


def inspect_archive(source):
    mode = "r|*" if hasattr(source, "read") else "r:*"
    kwargs = {"fileobj": source} if hasattr(source, "read") else {"name": source}
    files = 0
    total_size = 0
    with tarfile.open(mode=mode, **kwargs) as archive:
        for member in archive:
            validate_name(member.name)
            if member.isdir():
                continue
            if not member.isfile():
                raise ArchivePolicyError(
                    f"forbidden archive member kind: {member.name!r}"
                )
            if member.size > MAX_MEMBER_SIZE:
                raise ArchivePolicyError(
                    f"forbidden archive member size: {member.name!r} ({member.size} bytes)"
                )
            handle = archive.extractfile(member)
            if handle is None:
                raise ArchivePolicyError(f"cannot read archive member: {member.name!r}")
            content = handle.read()
            total_size += len(content)
            files += 1
            for pattern in PRIVATE_CONTENT_PATTERNS:
                if pattern.search(content):
                    raise ArchivePolicyError(
                        f"private content in archive member: {member.name!r}"
                    )
    if files == 0:
        raise ArchivePolicyError("archive contains no regular files")
    return {"files": files, "bytes": total_size}


def main():
    parser = argparse.ArgumentParser(
        description="Reject private, generated, or unsafe members in a source archive"
    )
    parser.add_argument("archive", help="tar archive path, or - for standard input")
    args = parser.parse_args()
    source = sys.stdin.buffer if args.archive == "-" else args.archive
    try:
        result = inspect_archive(source)
    except (ArchivePolicyError, tarfile.TarError) as error:
        parser.error(str(error))
    print(f"archive policy passed: {result['files']} files, {result['bytes']} bytes")


if __name__ == "__main__":
    main()
