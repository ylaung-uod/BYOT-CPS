#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render_fetch_help(manifest):
    installer = next(
        item for item in manifest["images"] if item["source"] == "vendor-download"
    )
    archive = installer["archive"]
    return "\n".join(
        [
            "BYOT-CPS external artifact acquisition",
            "",
            "1. Open the official Netgate Store page:",
            f"   {installer['download_page']}",
            "2. Sign in, select AMD64 ISO for virtual machines, and complete the free checkout.",
            f"3. Obtain the pinned archive: {archive['name']}",
            "4. Compare its compressed SHA-256 with the pinned value:",
            f"   {archive['sha256']}",
            "   Official checksums:",
            f"   {installer['current_checksums']}",
            "   Expected SHA-256 after decompression:",
            f"   {installer['sha256']}",
            "   Review Netgate's license terms before use:",
            f"   {installer['license_terms']}",
            "5. Save the archive under downloads/ or pass its path explicitly:",
            f"   make prepare-images PFSENSE_INSTALLER_ARCHIVE=/path/to/{archive['name']}",
            "6. Verify the installed ISO and generated blank disk:",
            "   make verify-images",
            "",
            "The project does not download or redistribute the Netgate installer.",
        ]
    )


def main():
    parser = argparse.ArgumentParser(
        description="Print authoritative acquisition links for external artifacts"
    )
    parser.add_argument("--manifest", type=Path, default=ROOT / "images.json")
    args = parser.parse_args()
    print(render_fetch_help(json.loads(args.manifest.read_text())))


if __name__ == "__main__":
    main()
