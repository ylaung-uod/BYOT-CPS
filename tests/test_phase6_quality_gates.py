import ast
import io
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class PhaseSixQualityGateTests(unittest.TestCase):
    def test_pull_request_ci_covers_every_phase_six_gate_with_pinned_actions(self):
        workflow = ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(workflow.is_file())
        text = workflow.read_text()
        self.assertIn("pull_request:", text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertEqual(
            text.count("ref: ${{ github.event.pull_request.head.sha || github.sha }}"),
            2,
        )
        self.assertEqual(text.count("persist-credentials: false"), 2)
        for command in (
            "make ci-static",
            "make container-ci",
            "git diff --check",
            "git archive",
            "src/inspect_archive.py",
        ):
            self.assertIn(command, text)
        for action, revision in re.findall(r"uses:\s*([^@\s]+)@([^\s#]+)", text):
            with self.subTest(action=action):
                self.assertRegex(revision, r"^[0-9a-f]{40}$")

    def test_hosted_static_job_installs_native_test_dependencies(self):
        text = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn("sudo apt-get update", text)
        self.assertIn("sudo apt-get install --no-install-recommends", text)
        for package in ("dosfstools", "mtools", "qemu-utils"):
            with self.subTest(package=package):
                self.assertIn(package, text)

    def test_release_and_live_targets_cover_local_and_gns3_gates_separately(self):
        makefile = (ROOT / "Makefile").read_text()
        for target in (
            "validate-data",
            "markdown-link-check",
            "external-link-check",
            "python-static",
            "workflow-lint",
            "secret-scan",
            "dockerfile-lint",
            "archive-inspect",
            "ci-static",
            "container-ci",
            "release-check",
            "live-release-check",
        ):
            self.assertRegex(makefile, rf"(?m)^{re.escape(target)}\s*:(?:[^=].*)?$")
        release_recipe = makefile.split("release-check:", 1)[1].split("\n\n", 1)[0]
        for gate in (
            "validate-data",
            "test",
            "markdown-link-check",
            "external-link-check",
            "python-static",
            "workflow-lint",
            "secret-scan",
            "dockerfile-lint",
            "archive-inspect",
            "container-sboms-check",
            "container-runtime-test",
        ):
            self.assertIn(gate, release_recipe)
        self.assertIn("$(MAKE) validate validate-data", release_recipe)
        self.assertRegex(makefile, r"(?m)^ci-static: validate validate-data ")
        self.assertIn("RELEASE CHECK: PASSED", release_recipe)
        self.assertIn("RELEASE CHECK: FAILED", release_recipe)

        live_recipe = makefile.split("live-release-check:", 1)[1].split("\n\n", 1)[0]
        self.assertIn("templates", live_recipe)
        self.assertIn("src/live_release_check.py", live_recipe)
        live_script = (ROOT / "src" / "live_release_check.py").read_text()
        self.assertIn("(0, 1, 3, 10)", live_script)
        self.assertIn("byot-cps-smoke-", live_script)

    def test_archive_inspector_rejects_forbidden_release_members(self):
        from src.inspect_archive import ArchivePolicyError, inspect_archive

        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            payload = b"private appliance state"
            member = tarfile.TarInfo("images/private.qcow2")
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        stream.seek(0)
        with self.assertRaisesRegex(ArchivePolicyError, "forbidden archive member"):
            inspect_archive(stream)

    def test_archive_inspector_rejects_opaque_key_containers(self):
        from src.inspect_archive import ArchivePolicyError, inspect_archive

        for name in (
            "config/client.der",
            "config/client.key",
            "config/client.p12",
            "config/client.pkcs12",
            "config/client.pfx",
            "config/client.jks",
            "config/client.kdb",
            "config/client.kdbx",
            "config/client.keystore",
            "config/client.p8",
            "config/client.pk8",
            "config/client.pkcs8",
            "config/client.ppk",
        ):
            with self.subTest(name=name):
                stream = io.BytesIO()
                with tarfile.open(fileobj=stream, mode="w") as archive:
                    payload = b"opaque key container"
                    member = tarfile.TarInfo(name)
                    member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
                stream.seek(0)
                with self.assertRaisesRegex(ArchivePolicyError, "forbidden archive member"):
                    inspect_archive(stream)

    def test_archive_inspector_rejects_case_variant_private_directories(self):
        from src.inspect_archive import ArchivePolicyError, inspect_archive

        for name in ("Secrets/private.txt", "DOWNLOADS/image.txt", ".STATE/run.json"):
            with self.subTest(name=name):
                stream = io.BytesIO()
                with tarfile.open(fileobj=stream, mode="w") as archive:
                    payload = b"private state"
                    member = tarfile.TarInfo(name)
                    member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
                stream.seek(0)
                with self.assertRaisesRegex(ArchivePolicyError, "forbidden archive member"):
                    inspect_archive(stream)

    def test_archive_inspector_allows_the_documented_images_directory(self):
        from src.inspect_archive import inspect_archive

        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            directory = tarfile.TarInfo("images")
            directory.type = tarfile.DIRTYPE
            archive.addfile(directory)
            payload = b"Downloaded images are intentionally excluded."
            member = tarfile.TarInfo("images/README.md")
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        stream.seek(0)
        self.assertEqual(inspect_archive(stream)["files"], 1)

    def test_archive_inspector_rejects_cross_platform_private_material(self):
        from src.inspect_archive import ArchivePolicyError, inspect_archive

        payloads = (
            b"C:" + b"\\Users\\alice\\private-lab.txt",
            b"-----BEGIN DSA "
            + b"PRIVATE KEY-----\ndata\n-----END DSA PRIVATE KEY-----",
            b"-----BEGIN ENCRYPTED "
            + b"PRIVATE KEY-----\ndata\n-----END ENCRYPTED PRIVATE KEY-----",
            b"-----BEGIN PGP PRIVATE "
            + b"KEY BLOCK-----\ndata\n-----END PGP PRIVATE KEY BLOCK-----",
        )
        for payload in payloads:
            with self.subTest(payload=payload.splitlines()[0]):
                stream = io.BytesIO()
                with tarfile.open(fileobj=stream, mode="w") as archive:
                    member = tarfile.TarInfo("docs/example.txt")
                    member.size = len(payload)
                    archive.addfile(member, io.BytesIO(payload))
                stream.seek(0)
                with self.assertRaisesRegex(ArchivePolicyError, "private content"):
                    inspect_archive(stream)

    def test_live_cleanup_accepts_a_delete_timeout_only_after_absence_readback(self):
        from src.gns3_cleanup import delete_project_and_confirm

        class Api:
            def delete(self, path):
                raise TimeoutError("server completed deletion after client timeout")

            def get(self, path):
                self.assert_projects_path = path
                return []

        api = Api()
        delete_project_and_confirm(api, "project-id", "byot-cps-smoke-timeout")
        self.assertEqual(api.assert_projects_path, "/projects")

    def test_live_cleanup_waits_for_asynchronous_project_disappearance(self):
        from src.gns3_cleanup import delete_project_and_confirm

        class Api:
            def __init__(self):
                self.reads = 0

            def delete(self, path):
                raise TimeoutError("deletion still running")

            def get(self, path):
                self.reads += 1
                if self.reads == 1:
                    return [
                        {
                            "project_id": "project-id",
                            "name": "byot-cps-smoke-async",
                        }
                    ]
                return []

        api = Api()
        delays = []
        delete_project_and_confirm(
            api,
            "project-id",
            "byot-cps-smoke-async",
            attempts=3,
            delay=0.25,
            sleep=delays.append,
        )
        self.assertEqual(api.reads, 2)
        self.assertEqual(delays, [0.25])

    def test_failed_topology_build_confirms_partial_project_cleanup(self):
        from src.create_topology import build

        class Api:
            def __init__(self):
                self.project_reads = 0

            def get(self, path):
                if path == "/projects":
                    self.project_reads += 1
                    return []
                if path == "/templates":
                    return []
                raise AssertionError(path)

            def post(self, path, payload=None):
                if path == "/projects":
                    return {"project_id": "partial-id"}
                if path == "/projects/partial-id/open":
                    return {}
                raise AssertionError(path)

            def delete(self, path):
                self.deleted = path

        api = Api()
        with self.assertRaisesRegex(RuntimeError, "Missing GNS3 template"):
            build(api, "byot-cps-smoke-partial", 0)
        self.assertEqual(api.deleted, "/projects/partial-id")
        self.assertEqual(api.project_reads, 2)

    def test_live_release_checks_for_leftovers_when_smoke_subprocess_fails(self):
        from src.live_release_check import run

        class Api:
            def __init__(self):
                self.project_reads = 0

            def get(self, path):
                self.project_reads += 1
                return []

        def fail(command, **kwargs):
            raise subprocess.CalledProcessError(1, command)

        api = Api()
        with self.assertRaises(subprocess.CalledProcessError):
            run(api, counts=(0,), command_runner=fail)
        self.assertEqual(api.project_reads, 2)

    def test_local_quality_gates_validate_data_links_and_python(self):
        from src.quality_gates import check_data, check_markdown, check_python

        self.assertGreater(check_data(ROOT), 0)
        self.assertGreater(check_markdown(ROOT), 0)
        self.assertGreater(check_python(ROOT), 0)

    def test_local_quality_gates_fail_when_a_tracked_path_is_missing(self):
        from src.quality_gates import QualityGateError, repository_files

        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            tracked = repository / "tracked.md"
            tracked.write_text("tracked\n")
            subprocess.run(["git", "add", "tracked.md"], cwd=repository, check=True)
            tracked.unlink()

            with self.assertRaisesRegex(QualityGateError, "missing tracked path: tracked.md"):
                repository_files(repository)

    def test_runtime_gates_do_not_use_optimization_sensitive_assertions(self):
        offenders = {}
        for path in (ROOT / "src").glob("*.py"):
            lines = [
                node.lineno
                for node in ast.walk(ast.parse(path.read_bytes(), str(path)))
                if isinstance(node, ast.Assert)
            ]
            if lines:
                offenders[path.name] = lines
        self.assertEqual(offenders, {})

    def test_release_checks_are_documented_for_independent_maintainers(self):
        release_doc = ROOT / "docs" / "RELEASE-CHECKS.md"
        self.assertTrue(release_doc.is_file())
        text = release_doc.read_text()
        for expected in (
            "make release-check",
            "make live-release-check",
            "0, 1, 3, and 10",
            "self-hosted",
            "no temporary projects remain",
            "RELEASE CHECK: PASSED",
            "LIVE GNS3 RELEASE CHECK: PASSED",
        ):
            self.assertIn(expected, text)
        readme = (ROOT / "README.md").read_text()
        contributing = (ROOT / "CONTRIBUTING.md").read_text()
        self.assertIn("docs/RELEASE-CHECKS.md", readme)
        self.assertIn("make release-check", contributing)
        self.assertIn("make live-release-check", contributing)


if __name__ == "__main__":
    unittest.main()
