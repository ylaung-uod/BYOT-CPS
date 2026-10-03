#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]*\]\(([^)\s]+)(?:\s+['\"][^'\"]*['\"])?\)")
FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


class QualityGateError(ValueError):
    pass


def repository_files(root):
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    paths = []
    for encoded in result.stdout.split(b"\0"):
        if encoded:
            path = root / encoded.decode("utf-8", "surrogateescape")
            if path.exists():
                paths.append(path)
    return paths


def check_data(root=ROOT):
    checked = 0
    errors = []
    for path in repository_files(root):
        try:
            if path.suffix == ".json":
                json.loads(path.read_text())
                checked += 1
            elif path.suffix == ".xml":
                ET.parse(path)
                checked += 1
        except (OSError, UnicodeError, json.JSONDecodeError, ET.ParseError) as error:
            errors.append(f"{path.relative_to(root)}: {error}")
    if errors:
        raise QualityGateError("invalid JSON/XML:\n" + "\n".join(errors))
    return checked


def check_markdown(root=ROOT):
    checked = 0
    errors = []
    root = root.resolve()
    for path in repository_files(root):
        if path.suffix.lower() != ".md":
            continue
        checked += 1
        text = FENCED_CODE.sub("", path.read_text())
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip("<>")
            if not target or target.startswith("#"):
                continue
            if URI_SCHEME.match(target) or target.startswith("//"):
                continue
            relative = urllib.parse.unquote(target.split("#", 1)[0])
            resolved = (path.parent / relative).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(f"{path.relative_to(root)}: link escapes repository: {target}")
                continue
            if not resolved.exists():
                errors.append(f"{path.relative_to(root)}: missing link target: {target}")
    if errors:
        raise QualityGateError("invalid Markdown links:\n" + "\n".join(errors))
    return checked


def check_python(root=ROOT):
    checked = 0
    errors = []
    for path in repository_files(root):
        if path.suffix != ".py":
            continue
        checked += 1
        try:
            compile(path.read_bytes(), str(path.relative_to(root)), "exec")
        except (OSError, SyntaxError) as error:
            errors.append(f"{path.relative_to(root)}: {error}")
    if errors:
        raise QualityGateError("invalid Python:\n" + "\n".join(errors))
    return checked


def main():
    parser = argparse.ArgumentParser(description="Run dependency-free repository quality gates")
    parser.add_argument("gate", choices=("data", "markdown", "python"))
    args = parser.parse_args()
    checks = {
        "data": (check_data, "JSON/XML files"),
        "markdown": (check_markdown, "Markdown files"),
        "python": (check_python, "Python files"),
    }
    check, label = checks[args.gate]
    try:
        count = check(ROOT)
    except QualityGateError as error:
        parser.error(str(error))
    print(f"{args.gate} gate passed: {count} {label}")


if __name__ == "__main__":
    main()
