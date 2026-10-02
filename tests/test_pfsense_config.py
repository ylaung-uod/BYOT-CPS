import hashlib
import crypt
import ipaddress
import json
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pfsense_config
from pfsense_config import ConfigError, build_config_drive, render_config_with_dummy_admin, validate_config


VALID_CONFIG = """<?xml version="1.0"?>
<pfsense>
  <version>24.0</version>
  <system>
    <user>
      <name>admin</name>
      <descr>System Administrator</descr>
      <uid>0</uid>
      <bcrypt-hash>$2b$12$oldoldoldoldoldoldoldueJpV7n1Q9Uq6G2S2QwQbZ6E6J</bcrypt-hash>
    </user>
  </system>
  <interfaces>
    <wan><if>em0</if><ipaddr>dhcp</ipaddr></wan>
    <lan><if>em1</if><ipaddr>192.168.99.1</ipaddr><subnet>24</subnet></lan>
    <opt1><if>em2</if><ipaddr>172.20.0.1</ipaddr><subnet>24</subnet></opt1>
    <opt2><if>em3</if><ipaddr>10.0.0.1</ipaddr><subnet>24</subnet></opt2>
  </interfaces>
</pfsense>
"""


class PfSenseConfigTests(unittest.TestCase):
    def write_config(self, directory, content=VALID_CONFIG):
        path = Path(directory) / "config.xml"
        path.write_text(content)
        path.chmod(0o600)
        return path

    def test_validator_accepts_expected_four_adapter_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            result = validate_config(self.write_config(directory))
        self.assertEqual(result["version"], "24.0")
        self.assertEqual(result["interfaces"], {
            "wan": "em0",
            "lan": "em1",
            "opt1": "em2",
            "opt2": "em3",
        })

    def test_validator_rejects_an_interface_mapping_change(self):
        changed = VALID_CONFIG.replace("<if>em3</if>", "<if>em4</if>")
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, changed)
            with self.assertRaisesRegex(ConfigError, "interface mapping"):
                validate_config(path)

    def test_validator_rejects_group_or_world_readable_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory)
            path.chmod(0o644)
            with self.assertRaisesRegex(ConfigError, "permissions"):
                validate_config(path)

    def test_builder_places_exact_xml_on_partitioned_fat_media(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.write_config(directory)
            image = Path(directory) / "pfsense-config.img"
            build_config_drive(config, image)
            self.assertTrue(image.is_file())
            listing = subprocess.run(
                ["mdir", "-i", f"{image}@@1048576", "::/config"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertIn("config", listing.lower())
            extracted = Path(directory) / "restored.xml"
            subprocess.run(
                ["mcopy", "-o", "-i", f"{image}@@1048576", "::/config/config.xml", str(extracted)],
                check=True,
            )
            root = __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).parse(extracted).getroot()
            user = next(user for user in root.findall("./system/user") if user.findtext("name") == "admin")
            password_hash = user.findtext("bcrypt-hash")
            self.assertEqual(crypt.crypt("admin", password_hash), password_hash)

    def test_dummy_admin_render_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.write_config(directory)
            first = Path(directory) / "first.xml"
            second = Path(directory) / "second.xml"
            render_config_with_dummy_admin(config, first)
            render_config_with_dummy_admin(config, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            root = __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).parse(first).getroot()
            user = next(user for user in root.findall("./system/user") if user.findtext("uid") == "0")
            self.assertEqual(user.findtext("name"), "admin")
            password_hash = user.findtext("bcrypt-hash")
            self.assertEqual(crypt.crypt("admin", password_hash), password_hash)

    def test_builder_is_byte_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self.write_config(directory)
            first = Path(directory) / "first.img"
            second = Path(directory) / "second.img"
            build_config_drive(config, first)
            time.sleep(2.1)
            build_config_drive(config, second)
            self.assertEqual(hashlib.sha256(first.read_bytes()).hexdigest(), hashlib.sha256(second.read_bytes()).hexdigest())

    def test_public_drive_is_reproducible_and_semantically_matches_public_source(self):
        source = ROOT / "config" / "pfsense-public.xml"
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.img"
            second = Path(directory) / "second.img"
            extracted = Path(directory) / "config.xml"
            build_config_drive(source, first)
            build_config_drive(source, second)
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest(),
            )
            subprocess.run(
                [
                    "mcopy",
                    "-o",
                    "-i",
                    f"{first}@@1048576",
                    "::/config/config.xml",
                    str(extracted),
                ],
                check=True,
            )
            self.assertEqual(
                ET.canonicalize(from_file=source, strip_text=True),
                ET.canonicalize(from_file=extracted, strip_text=True),
            )

    def test_pfsense_template_attaches_generated_config_drive(self):
        templates = json.loads((ROOT / "gns3_templates.json").read_text())["templates"]
        payload = next(item["payload"] for item in templates if item["key"] == "pfsense")
        self.assertEqual(payload["hdb_disk_image"], "pfsense-config.img")
        self.assertEqual(payload["hdb_disk_interface"], "ide")
        self.assertEqual(payload["boot_priority"], "d")
        self.assertIn("admin / admin", payload["usage"])

    def test_make_prepares_config_drive_before_templates(self):
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn("pfsense-config-drive:", makefile)
        templates_rule = next(line for line in makefile.splitlines() if line.startswith("templates:"))
        self.assertIn("pfsense-config-drive", templates_rule)

    def test_makefile_exposes_the_complete_test_suite(self):
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn("test:\n\t$(PYTHON) -m unittest discover -s tests -v", makefile)

    def test_default_build_uses_the_tracked_public_configuration(self):
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn("PFSENSE_CONFIG ?= config/pfsense-public.xml", makefile)
        public_config = ROOT / "config" / "pfsense-public.xml"
        self.assertTrue(public_config.is_file())
        result = validate_config(public_config)
        self.assertEqual(result["interfaces"], {
            "wan": "em0",
            "lan": "em1",
            "opt1": "em2",
            "opt2": "em3",
        })

    def test_public_configuration_uses_private_internal_ipv4_addresses(self):
        root = __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).parse(
            ROOT / "config" / "pfsense-public.xml"
        ).getroot()
        for name in ("lan", "opt1", "opt2"):
            address = root.findtext(f"./interfaces/{name}/ipaddr")
            self.assertTrue(ipaddress.ip_address(address).is_private, (name, address))

    def test_public_configuration_blocks_internal_initiation_to_management(self):
        root = ET.parse(ROOT / "config" / "pfsense-public.xml").getroot()
        rules = root.findall("./filter/rule")
        for interface in ("opt1", "opt2"):
            with self.subTest(interface=interface):
                block_index = next(
                    index
                    for index, rule in enumerate(rules)
                    if rule.findtext("type") == "block"
                    and rule.findtext("interface") == interface
                    and rule.findtext("destination/network") == "lan"
                )
                pass_index = next(
                    index
                    for index, rule in enumerate(rules)
                    if rule.findtext("type") == "pass"
                    and rule.findtext("interface") == interface
                )
                self.assertLess(block_index, pass_index)

    def test_public_configuration_rejects_missing_management_isolation_rule(self):
        public_xml = (ROOT / "config" / "pfsense-public.xml").read_text()
        changed = public_xml.replace(
            "<type>block</type><interface>opt1</interface>",
            "<type>pass</type><interface>opt1</interface>",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, changed)
            original = pfsense_config.PUBLIC_CONFIG_PATH
            pfsense_config.PUBLIC_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(ConfigError, "management isolation"):
                    validate_config(path)
            finally:
                pfsense_config.PUBLIC_CONFIG_PATH = original

    def test_public_configuration_enables_dns_resolver_on_internal_interfaces(self):
        root = ET.parse(ROOT / "config" / "pfsense-public.xml").getroot()
        unbound = root.find("unbound")
        if unbound is None:
            self.fail("public configuration has no DNS Resolver declaration")
        self.assertIsNotNone(unbound.find("enable"))
        self.assertEqual(unbound.findtext("active_interface"), "lan,opt1,opt2")
        self.assertEqual(unbound.findtext("outgoing_interface"), "wan")

    def test_public_configuration_does_not_enable_plaintext_web_management(self):
        root = __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).parse(
            ROOT / "config" / "pfsense-public.xml"
        ).getroot()
        self.assertNotEqual(root.findtext("./system/webgui/protocol"), "http")

    def test_public_configuration_declares_the_administrator_groups(self):
        root = __import__("xml.etree.ElementTree", fromlist=["ElementTree"]).parse(
            ROOT / "config" / "pfsense-public.xml"
        ).getroot()
        groups = {group.findtext("name"): group for group in root.findall("./system/group")}
        self.assertEqual(set(groups), {"all", "admins"})
        self.assertEqual(groups["admins"].findtext("member"), "0")
        self.assertEqual(groups["admins"].findtext("priv"), "page-all")

    def test_world_readable_public_configuration_rejects_certificate_material(self):
        public_xml = (ROOT / "config" / "pfsense-public.xml").read_text()
        changed = public_xml.replace("</pfsense>", "<cert><crt>PUBLIC-CERT</crt><prv>PRIVATE-KEY</prv></cert></pfsense>")
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, changed)
            path.chmod(0o644)
            original = pfsense_config.PUBLIC_CONFIG_PATH
            pfsense_config.PUBLIC_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(ConfigError, "public configuration contains forbidden"):
                    validate_config(path)
            finally:
                pfsense_config.PUBLIC_CONFIG_PATH = original

    def test_public_configuration_rejects_cleartext_password_elements(self):
        public_xml = (ROOT / "config" / "pfsense-public.xml").read_text()
        changed = public_xml.replace("</pfsense>", "<password>not-public</password></pfsense>")
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, changed)
            original = pfsense_config.PUBLIC_CONFIG_PATH
            pfsense_config.PUBLIC_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(ConfigError, "public configuration contains forbidden"):
                    validate_config(path)
            finally:
                pfsense_config.PUBLIC_CONFIG_PATH = original

    def test_public_configuration_rejects_unlisted_pfsense_secret_fields(self):
        public_xml = (ROOT / "config" / "pfsense-public.xml").read_text()
        for tag in ("ipsecpsk", "rocommunity", "ddnsdomainkey"):
            with self.subTest(tag=tag), tempfile.TemporaryDirectory() as directory:
                changed = public_xml.replace("</pfsense>", f"<{tag}>not-public</{tag}></pfsense>")
                path = self.write_config(directory, changed)
                original = pfsense_config.PUBLIC_CONFIG_PATH
                pfsense_config.PUBLIC_CONFIG_PATH = path
                try:
                    with self.assertRaisesRegex(ConfigError, "public configuration contains forbidden"):
                        validate_config(path)
                finally:
                    pfsense_config.PUBLIC_CONFIG_PATH = original

    def test_private_mode_does_not_bypass_public_configuration_safety_checks(self):
        public_xml = (ROOT / "config" / "pfsense-public.xml").read_text()
        changed = public_xml.replace("</pfsense>", "<cert><crt>PUBLIC-CERT</crt></cert></pfsense>")
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, changed)
            original = pfsense_config.PUBLIC_CONFIG_PATH
            pfsense_config.PUBLIC_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(ConfigError, "public configuration contains forbidden"):
                    validate_config(path)
            finally:
                pfsense_config.PUBLIC_CONFIG_PATH = original

    def test_world_readable_public_configuration_requires_the_dummy_admin_hash(self):
        public_xml = (ROOT / "config" / "pfsense-public.xml").read_text()
        changed = public_xml.replace(pfsense_config.DUMMY_ADMIN_BCRYPT_HASH, "$2b$12$not-the-dummy-public-lab-hash")
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, changed)
            path.chmod(0o644)
            original = pfsense_config.PUBLIC_CONFIG_PATH
            pfsense_config.PUBLIC_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(ConfigError, "dummy administrator"):
                    validate_config(path)
            finally:
                pfsense_config.PUBLIC_CONFIG_PATH = original

    def test_public_configuration_rejects_duplicate_password_hash_elements(self):
        public_xml = (ROOT / "config" / "pfsense-public.xml").read_text()
        changed = public_xml.replace(
            "</user>",
            "<bcrypt-hash>$2b$12$not-public</bcrypt-hash></user>",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, changed)
            original = pfsense_config.PUBLIC_CONFIG_PATH
            pfsense_config.PUBLIC_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(ConfigError, "duplicate element"):
                    validate_config(path)
            finally:
                pfsense_config.PUBLIC_CONFIG_PATH = original

    def test_public_configuration_rejects_additional_user_accounts(self):
        public_xml = (ROOT / "config" / "pfsense-public.xml").read_text()
        extra_user = "<user><name>unexpected</name><uid>2000</uid><bcrypt-hash>private</bcrypt-hash></user>"
        changed = public_xml.replace("</system>", extra_user + "</system>")
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, changed)
            original = pfsense_config.PUBLIC_CONFIG_PATH
            pfsense_config.PUBLIC_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(ConfigError, "duplicate element|exactly one user"):
                    validate_config(path)
            finally:
                pfsense_config.PUBLIC_CONFIG_PATH = original

    def test_world_readable_public_configuration_rejects_pem_material_in_any_element(self):
        public_xml = (ROOT / "config" / "pfsense-public.xml").read_text()
        changed = public_xml.replace(
            "Public synthetic BYOT-CPS baseline; contains no production configuration",
            "-----BEGIN PRIVATE KEY-----",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, changed)
            path.chmod(0o644)
            original = pfsense_config.PUBLIC_CONFIG_PATH
            pfsense_config.PUBLIC_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(ConfigError, "PEM material"):
                    validate_config(path)
            finally:
                pfsense_config.PUBLIC_CONFIG_PATH = original

    def test_public_configuration_rejects_pem_material_in_element_tail(self):
        public_xml = (ROOT / "config" / "pfsense-public.xml").read_text()
        changed = public_xml.replace(
            "</description>",
            "</description>-----BEGIN PRIVATE KEY-----",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, changed)
            original = pfsense_config.PUBLIC_CONFIG_PATH
            pfsense_config.PUBLIC_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(ConfigError, "PEM material"):
                    validate_config(path)
            finally:
                pfsense_config.PUBLIC_CONFIG_PATH = original


if __name__ == "__main__":
    unittest.main()
