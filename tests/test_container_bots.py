import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from export_project import export

ROOT = Path(__file__).resolve().parents[1]
COMPROMISED_IOT_NAMES = {"COMPROMISED-IOT-01", "COMPROMISED-IOT-02", "COMPROMISED-IOT-03"}
SOURCE_UBUNTU24_NAMES = {
    "PC1": "CPS-OPERATOR",
    "EXTERNAL-PC": "EXTERNAL-CLIENT",
    "IT-ADMIN": "MGMT-ADMIN",
    "ExploitPC": "RED-TEAM-HOST",
}
UBUNTU24_CONTAINER_NAMES = set(SOURCE_UBUNTU24_NAMES.values())


class ContainerBotTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.topology = json.loads((ROOT / "topology.json").read_text())
        cls.templates = {
            item["key"]: item
            for item in json.loads((ROOT / "gns3_templates.json").read_text())["templates"]
        }

    def test_three_compromised_iot_nodes_use_docker_template(self):
        bots = {n["name"]: n for n in self.topology["nodes"] if n["name"] in COMPROMISED_IOT_NAMES}
        self.assertEqual(set(bots), COMPROMISED_IOT_NAMES)
        for node in bots.values():
            self.assertEqual(node["node_type"], "docker")
            self.assertEqual(node["template"], "ubuntu18_lab")

    def test_c2_uses_ubuntu_18_docker_template(self):
        c2 = next(n for n in self.topology["nodes"] if n["name"] == "C2-SIMULATOR")
        self.assertEqual(c2["node_type"], "docker")
        self.assertEqual(c2["template"], "ubuntu18_lab")

    def test_pc1_uses_ubuntu_24_docker_template(self):
        nodes = {n["name"]: n for n in self.topology["nodes"] if n["name"] in UBUNTU24_CONTAINER_NAMES}
        self.assertEqual(set(nodes), UBUNTU24_CONTAINER_NAMES)
        for node in nodes.values():
            self.assertEqual(node["node_type"], "docker")
            self.assertEqual(node["template"], "ubuntu24_lab")

    def test_web_server_uses_dedicated_nginx_docker_template(self):
        node = next(n for n in self.topology["nodes"] if n["name"] == "DMZ-WEB-SERVER")
        self.assertEqual(node["node_type"], "docker")
        self.assertEqual(node["template"], "ubuntu24_web")

    def test_nginx_template_and_image_are_declared(self):
        self.assertIn("ubuntu24_web", self.templates)
        payload = self.templates["ubuntu24_web"]["payload"]
        self.assertEqual(payload["template_type"], "docker")
        self.assertEqual(payload["image"], "byot-cps/ubuntu24-nginx:latest")
        self.assertIn("HTTP", payload["usage"])
        dockerfile = ROOT / "Dockerfiles/ubuntu24-nginx/Dockerfile"
        entrypoint = ROOT / "Dockerfiles/ubuntu24-nginx/entrypoint.sh"
        self.assertTrue(dockerfile.is_file())
        self.assertTrue(entrypoint.is_file())
        self.assertIn("nginx", dockerfile.read_text())
        self.assertIn("/usr/sbin/nginx", entrypoint.read_text())

    def test_docker_template_uses_local_lab_image(self):
        payload = self.templates["ubuntu18_lab"]["payload"]
        self.assertEqual(payload["template_type"], "docker")
        self.assertEqual(payload["image"], "byot-cps/ubuntu18-lab:latest")
        self.assertEqual(payload["adapters"], 1)
        self.assertEqual(payload["console_type"], "telnet")

    def test_lab_image_definition_is_present_and_inert(self):
        dockerfile = (ROOT / "Dockerfiles/ubuntu18-lab/Dockerfile").read_text()
        entrypoint = (ROOT / "Dockerfiles/ubuntu18-lab/entrypoint.sh").read_text()
        self.assertIn(
            "FROM ubuntu:18.04@sha256:152dc042452c496007f07ca9127571cb9c29697f42acbfad72324b2bb2e43c98",
            dockerfile,
        )
        self.assertIn("sleep infinity", entrypoint)
        combined = (dockerfile + entrypoint).lower()
        self.assertNotIn("mirai", combined)
        self.assertNotIn("scanner", combined)

    def test_ubuntu_24_lab_template_and_image_are_present(self):
        payload = self.templates["ubuntu24_lab"]["payload"]
        self.assertEqual(payload["template_type"], "docker")
        self.assertEqual(payload["image"], "byot-cps/ubuntu24-lab:latest")
        dockerfile = (ROOT / "Dockerfiles/ubuntu24-lab/Dockerfile").read_text()
        self.assertIn(
            "FROM ubuntu:24.04@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517",
            dockerfile,
        )

    def test_make_builds_lab_image_before_creating_templates(self):
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn("docker-images:", makefile)
        self.assertIn("byot-cps/ubuntu24-nginx:latest", makefile)
        templates_rule = next(line for line in makefile.splitlines() if line.startswith("templates:"))
        self.assertIn("docker-images", templates_rule)

    def test_exporter_keeps_bot_nodes_containerized(self):
        source = {
            "name": "source",
            "scene_height": 1000,
            "scene_width": 2000,
            "show_grid": True,
            "show_interface_labels": False,
            "show_layers": False,
            "snap_to_grid": True,
            "topology": {
                "nodes": [{
                    "name": "MIRAI-BOT",
                    "node_id": "node-1",
                    "node_type": "qemu",
                    "template_id": "77c14d5d-e9b6-4fb8-9804-d5eb57fa084a",
                    "x": 0,
                    "y": 0,
                }],
                "links": [],
            },
        }
        with tempfile.NamedTemporaryFile("w", suffix=".gns3") as stream:
            json.dump(source, stream)
            stream.flush()
            node = export(stream.name)["nodes"][0]
        self.assertEqual(node["node_type"], "docker")
        self.assertEqual(node["template"], "ubuntu18_lab")
        self.assertEqual(node["name"], "COMPROMISED-IOT-01")

    def test_exporter_containerizes_c2_and_pc1(self):
        source = {
            "name": "source",
            "scene_height": 1000,
            "scene_width": 2000,
            "show_grid": True,
            "show_interface_labels": False,
            "show_layers": False,
            "snap_to_grid": True,
            "topology": {
                "nodes": [
                    {"name": "MIRAI-C2", "node_id": "c2", "node_type": "qemu", "template_id": "77c14d5d-e9b6-4fb8-9804-d5eb57fa084a", "x": 0, "y": 0},
                    {"name": "PC1", "node_id": "pc1", "node_type": "qemu", "template_id": "592a288d-be5f-42b5-a1d7-f64bfffd3773", "x": 1, "y": 1},
                ],
                "links": [],
            },
        }
        with tempfile.NamedTemporaryFile("w", suffix=".gns3") as stream:
            json.dump(source, stream)
            stream.flush()
            nodes = {node["name"]: node for node in export(stream.name)["nodes"]}
        self.assertEqual(nodes["C2-SIMULATOR"]["template"], "ubuntu18_lab")
        self.assertEqual(nodes["CPS-OPERATOR"]["template"], "ubuntu24_lab")
        self.assertEqual(nodes["C2-SIMULATOR"]["node_type"], "docker")
        self.assertEqual(nodes["CPS-OPERATOR"]["node_type"], "docker")

    def test_exporter_containerizes_all_ubuntu_24_desktops(self):
        source_nodes = []
        for index, name in enumerate(sorted(SOURCE_UBUNTU24_NAMES)):
            source_nodes.append({
                "name": name,
                "node_id": f"node-{index}",
                "node_type": "qemu",
                "template_id": "592a288d-be5f-42b5-a1d7-f64bfffd3773",
                "x": index,
                "y": index,
            })
        source = {
            "name": "source",
            "scene_height": 1000,
            "scene_width": 2000,
            "show_grid": True,
            "show_interface_labels": False,
            "show_layers": False,
            "snap_to_grid": True,
            "topology": {"nodes": source_nodes, "links": []},
        }
        with tempfile.NamedTemporaryFile("w", suffix=".gns3") as stream:
            json.dump(source, stream)
            stream.flush()
            nodes = export(stream.name)["nodes"]
        self.assertEqual({node["name"] for node in nodes}, UBUNTU24_CONTAINER_NAMES)
        self.assertTrue(all(node["node_type"] == "docker" for node in nodes))
        self.assertTrue(all(node["template"] == "ubuntu24_lab" for node in nodes))

    def test_only_used_templates_and_vm_images_are_required(self):
        used_templates = {node["template"] for node in self.topology["nodes"] if "template" in node}
        self.assertEqual(set(self.templates), used_templates)
        images = {item["name"] for item in json.loads((ROOT / "images.json").read_text())["images"]}
        self.assertNotIn("Ubuntu 24.04 (64bit).vmdk", images)
        self.assertNotIn("Ubuntu 18.04.6 (64bit).vmdk", images)
        self.assertNotIn("Ubuntu_Server_2404.qcow2", images)

    def test_exporter_containerizes_web_server(self):
        source = {
            "name": "source",
            "scene_height": 1000,
            "scene_width": 2000,
            "show_grid": True,
            "show_interface_labels": False,
            "show_layers": False,
            "snap_to_grid": True,
            "topology": {
                "nodes": [{
                    "name": "WEB-SERVER",
                    "node_id": "web",
                    "node_type": "qemu",
                    "template_id": "946d2523-3a32-4db9-aa66-327a22bd0f73",
                    "x": 0,
                    "y": 0,
                }],
                "links": [],
            },
        }
        with tempfile.NamedTemporaryFile("w", suffix=".gns3") as stream:
            json.dump(source, stream)
            stream.flush()
            node = export(stream.name)["nodes"][0]
        self.assertEqual(node["node_type"], "docker")
        self.assertEqual(node["template"], "ubuntu24_web")
        self.assertEqual(node["name"], "DMZ-WEB-SERVER")
    def test_all_container_images_define_dummy_sudo_user(self):
        for version in ("ubuntu18-lab", "ubuntu24-lab", "ubuntu24-nginx"):
            with self.subTest(version=version):
                dockerfile = (ROOT / f"Dockerfiles/{version}/Dockerfile").read_text()
                self.assertIn("sudo", dockerfile)
                self.assertIn("useradd", dockerfile)
                self.assertIn(
                    "usermod --password '$6$byotcps$ypK9Wt6JhQuEUL45vF7BrabMDI35pUOA6AHCVKV9fZfWxkItTYtR5W02Aq0Va9naZztO7YlIk6PcThgkEVUVH0' lab",
                    dockerfile,
                )
                self.assertNotIn("chpasswd", dockerfile)
                self.assertIn("usermod -aG sudo", dockerfile)
                self.assertNotIn("USER lab", dockerfile)
                entrypoint = (ROOT / f"Dockerfiles/{version}/entrypoint.sh").read_text()
                self.assertIn("exec chroot --userspec=lab:lab --groups=sudo / sleep infinity", entrypoint)
                self.assertNotIn("exec su -s /bin/sh lab", entrypoint)
        for key in ("ubuntu18_lab", "ubuntu24_lab", "ubuntu24_web"):
            usage = self.templates[key]["payload"]["usage"]
            self.assertIn("lab / lab", usage)
    def test_all_container_entrypoints_install_default_gateway_as_resolver(self):
        for version in ("ubuntu18-lab", "ubuntu24-lab", "ubuntu24-nginx"):
            with self.subTest(version=version):
                entrypoint = (ROOT / f"Dockerfiles/{version}/entrypoint.sh").read_text()
                self.assertIn("install_gateway_dns", entrypoint)
                self.assertIn("ip -4 route get 1.1.1.1", entrypoint)
                self.assertIn("Waiting for default route before starting services", entrypoint)
                self.assertIn("nameserver %s", entrypoint)
                self.assertIn("> /etc/resolv.conf", entrypoint)
                self.assertIn("\ninstall_gateway_dns\n", entrypoint)
                self.assertNotIn("install_gateway_dns &", entrypoint)

    def test_all_container_images_run_password_authenticated_ssh(self):
        for version in ("ubuntu18-lab", "ubuntu24-lab", "ubuntu24-nginx"):
            with self.subTest(version=version):
                dockerfile = (ROOT / f"Dockerfiles/{version}/Dockerfile").read_text()
                entrypoint = (ROOT / f"Dockerfiles/{version}/entrypoint.sh").read_text()
                self.assertIn("openssh-server", dockerfile)
                self.assertIn("PasswordAuthentication yes", dockerfile)
                self.assertIn("PermitRootLogin no", dockerfile)
                self.assertIn("rm -f /etc/ssh/ssh_host_", dockerfile)
                self.assertLess(dockerfile.index("rm -f /etc/ssh/ssh_host_"), dockerfile.index("RUN useradd"))
                self.assertIn("EXPOSE 22", dockerfile)
                self.assertIn("ssh-keygen -A", entrypoint)
                self.assertIn("/usr/sbin/sshd", entrypoint)
        for key in ("ubuntu18_lab", "ubuntu24_lab", "ubuntu24_web"):
            self.assertIn("SSH", self.templates[key]["payload"]["usage"])


if __name__ == "__main__":
    unittest.main()
