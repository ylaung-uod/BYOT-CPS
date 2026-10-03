import importlib
import importlib.util
import gzip
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class ImageArtifactTests(unittest.TestCase):
    def test_manifest_uses_sha256_and_declares_generated_blank_disk(self):
        manifest_text = (ROOT / "images.json").read_text()
        manifest = json.loads(manifest_text)
        self.assertEqual(manifest["algorithm"], "sha256")
        self.assertFalse(any("md5" in item for item in manifest["images"]))
        self.assertIn("legacy_marketplace_md5", manifest)

        by_name = {item["name"]: item for item in manifest["images"]}
        blank = by_name["pfSense.qcow2"]
        self.assertEqual(blank["source"], "generated")
        self.assertEqual(blank["format"], "qcow2")
        self.assertEqual(blank["virtual_size"], 100 * 1024**3)

        installer = by_name["netgate-installer-v1.2-RELEASE-amd64.iso"]
        self.assertEqual(
            installer["sha256"],
            "f55dc289eeda16c9698db092c93b3f26a36fdacaadc4fab67876530bd3aeae96",
        )
        self.assertEqual(installer["size"], 1059239936)
        self.assertEqual(
            installer["archive"]["sha256"],
            "184514fe7df0d339362c1e33fa051c464577a450528759b343ade894c7c57955",
        )
        self.assertEqual(installer["archive"]["size"], 342781760)
        templates = json.loads((ROOT / "gns3_templates.json").read_text())["templates"]
        pfsense = next(item for item in templates if item["key"] == "pfsense")
        self.assertEqual(pfsense["payload"]["cdrom_image"], installer["name"])

    def test_prepare_images_creates_blank_disk_and_verifies_archive_before_install(self):
        payload = b"synthetic installer payload"
        archive_buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=archive_buffer, mode="wb", mtime=0) as stream:
            stream.write(payload)
        archive_bytes = archive_buffer.getvalue()
        manifest = {
            "algorithm": "sha256",
            "images": [
                {
                    "name": "blank.qcow2",
                    "source": "generated",
                    "format": "qcow2",
                    "virtual_size": 8 * 1024**2,
                    "create_size": "8M",
                },
                {
                    "name": "installer.iso",
                    "source": "vendor-download",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload),
                    "archive": {
                        "name": "installer.iso.gz",
                        "sha256": hashlib.sha256(archive_bytes).hexdigest(),
                        "size": len(archive_bytes),
                    },
                },
            ],
        }

        self.assertIsNotNone(importlib.util.find_spec("prepare_images"))
        prepare_images = importlib.import_module("prepare_images")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "installer.iso.gz"
            archive.write_bytes(archive_bytes)
            image_dir = root / "images"

            prepare_images.prepare_images(manifest, image_dir, archive)
            prepare_images.prepare_images(manifest, image_dir, archive)

            self.assertEqual((image_dir / "installer.iso").read_bytes(), payload)
            info = json.loads(
                subprocess.run(
                    ["qemu-img", "info", "--output=json", str(image_dir / "blank.qcow2")],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout
            )
            self.assertEqual(info["format"], "qcow2")
            self.assertEqual(info["virtual-size"], 8 * 1024**2)

    def test_verifier_checks_sha256_and_generated_disk_properties(self):
        payload = b"verified installer"
        archive_buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=archive_buffer, mode="wb", mtime=0) as stream:
            stream.write(payload)
        archive_bytes = archive_buffer.getvalue()
        manifest = {
            "algorithm": "sha256",
            "images": [
                {
                    "name": "blank.qcow2",
                    "source": "generated",
                    "format": "qcow2",
                    "virtual_size": 8 * 1024**2,
                    "create_size": "8M",
                },
                {
                    "name": "installer.iso",
                    "source": "vendor-download",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size": len(payload),
                    "archive": {
                        "name": "installer.iso.gz",
                        "sha256": hashlib.sha256(archive_bytes).hexdigest(),
                        "size": len(archive_bytes),
                    },
                },
            ],
        }
        prepare_images = importlib.import_module("prepare_images")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "images.json"
            manifest_path.write_text(json.dumps(manifest))
            archive = root / "installer.iso.gz"
            archive.write_bytes(archive_bytes)
            image_dir = root / "images"
            prepare_images.prepare_images(manifest, image_dir, archive)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "src" / "verify_images.py"),
                    "--manifest",
                    str(manifest_path),
                    "--image-dir",
                    str(image_dir),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(result.stdout.count("OK"), 2)

    def test_generated_disk_with_allocated_guest_data_is_rejected(self):
        prepare_images = importlib.import_module("prepare_images")
        declaration = {
            "name": "blank.qcow2",
            "source": "generated",
            "format": "qcow2",
            "virtual_size": 8 * 1024**2,
            "create_size": "8M",
        }
        with tempfile.TemporaryDirectory() as directory:
            disk = Path(directory) / "blank.qcow2"
            prepare_images.create_blank_disk(disk, declaration)
            subprocess.run(
                ["qemu-io", "-f", "qcow2", "-c", "write 0 512", str(disk)],
                check=True,
                capture_output=True,
            )
            with self.assertRaisesRegex(prepare_images.ArtifactError, "not blank"):
                prepare_images.verify_blank_disk(disk, declaration)

    def test_generated_disk_with_backing_file_is_rejected(self):
        prepare_images = importlib.import_module("prepare_images")
        declaration = {
            "name": "blank.qcow2",
            "source": "generated",
            "format": "qcow2",
            "virtual_size": 8 * 1024**2,
            "create_size": "8M",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backing = root / "backing.raw"
            with backing.open("wb") as stream:
                stream.truncate(8 * 1024**2)
            disk = root / "blank.qcow2"
            subprocess.run(
                [
                    "qemu-img",
                    "create",
                    "-q",
                    "-f",
                    "qcow2",
                    "-F",
                    "raw",
                    "-b",
                    str(backing),
                    str(disk),
                ],
                check=True,
            )
            with self.assertRaisesRegex(prepare_images.ArtifactError, "backing file"):
                prepare_images.verify_blank_disk(disk, declaration)

    def test_fetch_help_and_make_targets_expose_manual_acquisition_workflow(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "src" / "fetch_help.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        for expected in (
            "https://shop.netgate.com/products/netgate-installer",
            "https://www.netgate.com/hubfs/pfSense-plus-installer-checksums.txt",
            "https://www.netgate.com/company/legal/eula",
            "netgate-installer-v1.2-RELEASE-amd64.iso.gz",
            "184514fe7df0d339362c1e33fa051c464577a450528759b343ade894c7c57955",
            "f55dc289eeda16c9698db092c93b3f26a36fdacaadc4fab67876530bd3aeae96",
            "make prepare-images",
        ):
            self.assertIn(expected, result.stdout)

        makefile = (ROOT / "Makefile").read_text()
        self.assertRegex(makefile, r"(?m)^fetch-help:")
        self.assertRegex(makefile, r"(?m)^prepare-images:")
        self.assertRegex(makefile, r"(?m)^verify-images:")
        self.assertIn("PFSENSE_INSTALLER_ARCHIVE ?=", makefile)

    def test_documentation_covers_official_acquisition_compatibility_and_licensing(self):
        documentation = "\n".join(
            (ROOT / path).read_text()
            for path in (
                "README.md",
                "docs/ARTIFACTS.md",
                "images/README.md",
                "pfsense/README.md",
            )
        )
        for expected in (
            "Netgate Store account",
            "checkout process",
            "netgate-installer-v1.2-RELEASE-amd64.iso.gz",
            "184514fe7df0d339362c1e33fa051c464577a450528759b343ade894c7c57955",
            "f55dc289eeda16c9698db092c93b3f26a36fdacaadc4fab67876530bd3aeae96",
            "https://docs.netgate.com/pfsense/en/latest/backup/restore.html",
            "https://www.netgate.com/company/legal/eula",
            "does not automate the store checkout",
            "make fetch-help",
            "make prepare-images",
            "make verify-images",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, documentation)


if __name__ == "__main__":
    unittest.main()
