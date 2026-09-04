import json
import runpy
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FakeAPI:
    def __init__(self, obsolete_field=False, preserve_obsolete=False):
        declarations = json.loads((ROOT / "gns3_templates.json").read_text())["templates"]
        self.existing = []
        for index, item in enumerate(declarations):
            template = dict(item["payload"])
            template["template_id"] = f"template-{index}"
            self.existing.append(template)
        self.existing[0]["boot_priority"] = "c"
        if obsolete_field:
            self.existing[0]["obsolete_owned_field"] = "legacy-value"
        self.preserve_obsolete = preserve_obsolete
        self.puts = []
        self.posts = []

    def get(self, path):
        if path == "/version":
            return {"version": "test"}
        if path == "/templates":
            return self.existing
        if path.startswith("/templates/"):
            template_id = path.rsplit("/", 1)[-1]
            return next(item for item in self.existing if item["template_id"] == template_id)
        raise AssertionError(path)

    def post(self, path, payload):
        self.posts.append((path, payload))
        return {**payload, "template_id": "created"}

    def put(self, path, payload):
        self.puts.append((path, payload))
        template_id = path.rsplit("/", 1)[-1]
        index = next(i for i, item in enumerate(self.existing) if item["template_id"] == template_id)
        updated = {**payload, "template_id": template_id}
        if self.preserve_obsolete and "obsolete_owned_field" in self.existing[index]:
            updated["obsolete_owned_field"] = self.existing[index]["obsolete_owned_field"]
        self.existing[index] = updated
        return updated


class TemplateReconciliationTests(unittest.TestCase):
    def test_existing_stale_template_is_updated_to_declared_payload(self):
        fake = FakeAPI()
        module = types.ModuleType("gns3_api")
        module.GNS3API = lambda: fake
        original = sys.modules.get("gns3_api")
        sys.modules["gns3_api"] = module
        try:
            runpy.run_path(str(ROOT / "src" / "create_templates.py"), run_name="__main__")
        finally:
            if original is None:
                del sys.modules["gns3_api"]
            else:
                sys.modules["gns3_api"] = original
        self.assertEqual(len(fake.puts), 1)
        path, payload = fake.puts[0]
        self.assertEqual(path, "/templates/template-0")
        self.assertEqual(payload["boot_priority"], "d")
        self.assertEqual(fake.posts, [])

    def test_existing_obsolete_payload_field_is_not_silently_accepted(self):
        fake = FakeAPI(obsolete_field=True)
        fake.existing[0]["boot_priority"] = "d"
        fake.existing[0]["qemu_path"] = "/usr/bin/qemu-system-x86_64"
        module = types.ModuleType("gns3_api")
        module.GNS3API = lambda: fake
        original = sys.modules.get("gns3_api")
        sys.modules["gns3_api"] = module
        try:
            runpy.run_path(str(ROOT / "src" / "create_templates.py"), run_name="__main__")
        finally:
            if original is None:
                del sys.modules["gns3_api"]
            else:
                sys.modules["gns3_api"] = original
        self.assertEqual(len(fake.puts), 1)
        self.assertNotIn("obsolete_owned_field", fake.puts[0][1])

    def test_unremovable_obsolete_field_fails_with_migration_instruction(self):
        fake = FakeAPI(obsolete_field=True, preserve_obsolete=True)
        fake.existing[0]["boot_priority"] = "d"
        fake.existing[0]["qemu_path"] = "/usr/bin/qemu-system-x86_64"
        module = types.ModuleType("gns3_api")
        module.GNS3API = lambda: fake
        original = sys.modules.get("gns3_api")
        sys.modules["gns3_api"] = module
        try:
            with self.assertRaisesRegex(RuntimeError, "Remove the stale owned template"):
                runpy.run_path(
                    str(ROOT / "src" / "create_templates.py"),
                    run_name="__main__",
                )
        finally:
            if original is None:
                del sys.modules["gns3_api"]
            else:
                sys.modules["gns3_api"] = original


if __name__ == "__main__":
    unittest.main()
