import re
import subprocess
import stat
import tarfile
import tempfile
import unittest
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


class PhaseSevenReleaseHygieneTests(unittest.TestCase):
    def test_public_release_metadata_declares_version_1_0_0(self):
        changelog = (ROOT / "CHANGELOG.md").read_text()
        self.assertIn("## [1.0.0] - 2026-09-04", changelog)
        self.assertNotIn("public template remains pre-1.0", changelog)

        citation = (ROOT / "CITATION.cff").read_text()
        self.assertIn("version: 1.0.0", citation)
        self.assertIn("date-released: 2026-09-04", citation)

        issue_template = (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").read_text()
        self.assertIn("placeholder: v1.0.0", issue_template)

    def test_release_notes_cover_every_phase_seven_disclosure(self):
        notes = ROOT / "docs" / "RELEASE-NOTES-v1.0.0.md"
        self.assertTrue(notes.is_file())
        text = notes.read_text()
        for expected in (
            "Public/private boundary",
            "External artifacts",
            "Supported versions",
            "Dummy credentials",
            "Interactive pfSense installation",
            "Verification results",
            "Repository history",
        ):
            self.assertIn(expected, text)
        self.assertIn("58 links", text)
        self.assertNotIn("recorded in its GitHub pull request and release record", text)

    def test_release_process_and_minimal_reproduction_archive(self):
        checks = (ROOT / "docs" / "RELEASE-CHECKS.md").read_text()
        for expected in (
            "clean clone",
            "release archive",
            "annotated `v1.0.0` tag",
            "verified commit",
            "GitHub release record",
            "GitHub API",
        ):
            self.assertIn(expected, checks)

        expected = {
            "CHANGELOG.md",
            "CITATION.cff",
            "CONTRIBUTING.md",
            "Dockerfiles/ubuntu18-lab/Dockerfile",
            "Dockerfiles/ubuntu18-lab/entrypoint.sh",
            "Dockerfiles/ubuntu18-lab/isrg-root-x1.pem",
            "Dockerfiles/ubuntu24-lab/Dockerfile",
            "Dockerfiles/ubuntu24-lab/entrypoint.sh",
            "Dockerfiles/ubuntu24-lab/isrg-root-x1.pem",
            "Dockerfiles/ubuntu24-nginx/Dockerfile",
            "Dockerfiles/ubuntu24-nginx/entrypoint.sh",
            "Dockerfiles/ubuntu24-nginx/isrg-root-x1.pem",
            "LICENSE",
            "Makefile",
            "NOTICE.md",
            "README.md",
            "REPRODUCTION.md",
            "REPRODUCTION-MANIFEST.sha256",
            "SECURITY.md",
            "config/pfsense-public.xml",
            "container_images.json",
            "docs/ARCHITECTURE.md",
            "docs/ARTIFACTS.md",
            "docs/CONTAINERS.md",
            "docs/REPRODUCIBILITY.md",
            "docs/RELEASE-CHECKS.md",
            "docs/RELEASE-NOTES-v1.0.0.md",
            "docs/SECURITY-BOUNDARY.md",
            "gns3_templates.json",
            "images.json",
            "images/README.md",
            "pfsense/README.md",
            "provenance.json",
            "requirements.txt",
            "sbom/ubuntu18-lab.spdx.json",
            "sbom/ubuntu24-lab.spdx.json",
            "sbom/ubuntu24-nginx.spdx.json",
            "src/create_templates.py",
            "src/create_topology.py",
            "src/fetch_help.py",
            "src/generate_container_sboms.py",
            "src/gns3_api.py",
            "src/gns3_cleanup.py",
            "src/pfsense_config.py",
            "src/prepare_images.py",
            "src/smoke_test.py",
            "src/test_container_images.py",
            "src/topology_transform.py",
            "src/validate.py",
            "src/verify_images.py",
            "topology.json",
        }
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "reproduction.tar.gz"
            command = [
                "make",
                "reproduction-archive",
                f"REPRODUCTION_ARCHIVE={archive}",
            ]
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True)
            first = archive.read_bytes()
            self.assertEqual(stat.S_IMODE(archive.stat().st_mode), 0o644)
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True)
            self.assertEqual(archive.read_bytes(), first)

            with tarfile.open(archive, "r:gz") as bundle:
                members = bundle.getmembers()
                self.assertTrue(all(member.isfile() for member in members))
                prefix = "byot-cps-v1.0.0/"
                self.assertTrue(all(member.name.startswith(prefix) for member in members))
                for member in members:
                    path = PurePosixPath(member.name)
                    self.assertFalse(path.is_absolute())
                    self.assertNotIn("..", path.parts)
                    self.assertEqual(member.mode, 0o644)
                    self.assertEqual((member.uid, member.gid), (0, 0))
                    self.assertEqual((member.uname, member.gname), ("", ""))
                    self.assertEqual(member.mtime, 0)
                self.assertEqual(
                    {member.name.removeprefix(prefix) for member in members}, expected
                )
                bundle.extractall(temporary, filter="data")

            extracted = Path(temporary) / "byot-cps-v1.0.0"
            broken_links = []
            for markdown in extracted.rglob("*.md"):
                for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", markdown.read_text()):
                    if target.startswith(("http://", "https://", "mailto:", "#")):
                        continue
                    relative = target.split("#", 1)[0]
                    if relative and not (markdown.parent / relative).is_file():
                        broken_links.append(f"{markdown.relative_to(extracted)}: {target}")
            self.assertEqual(broken_links, [])
            subprocess.run(
                ["sha256sum", "-c", "REPRODUCTION-MANIFEST.sha256"],
                cwd=extracted,
                check=True,
                capture_output=True,
            )
            subprocess.run(["make", "validate"], cwd=extracted, check=True)
            subprocess.run(
                ["make", "pfsense-config-validate"], cwd=extracted, check=True
            )

    def test_release_metadata_matches_the_snapshot_repository(self):
        notes = (ROOT / "docs" / "RELEASE-NOTES-v1.0.0.md").read_text()
        self.assertIn("110 unit tests", notes)
        self.assertIn("single root snapshot", notes)
        identities = subprocess.run(
            ["git", "log", "--format=%an%x00%ae"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertTrue(identities)
        for identity in identities:
            name, email = identity.split("\0", 1)
            self.assertTrue(name.strip())
            self.assertIn("@", email)
            self.assertFalse(email.endswith("@localhost"))
        self.assertNotIn("91 unit tests", notes)
        self.assertNotIn("93 unit tests", notes)
        self.assertNotIn("33817058239", notes)
        self.assertNotIn("existing history is preserved", notes)
        self.assertNotIn("Phase 6 hosted baseline", notes)

    def test_hosted_verification_supports_the_release_commit(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("github.event.pull_request.head.sha || github.sha", workflow)
        self.assertIn("if: github.event_name == 'pull_request'", workflow)

        makefile = (ROOT / "Makefile").read_text()
        expected_release_url = (
            "^https://github[.]com/ylaung-uod/byot-cps/releases/tag/v1[.]0[.]0$$"
        )
        self.assertEqual(
            [line for line in makefile.splitlines() if line.startswith("SELF_RELEASE_URL")],
            [f"SELF_RELEASE_URL ?= {expected_release_url}"],
        )

        lines = makefile.splitlines()
        target_index = lines.index("external-link-check:")
        recipe = []
        for line in lines[target_index + 1 :]:
            if not line.startswith("\t"):
                break
            recipe.append(line)
        self.assertEqual(
            recipe,
            [
                "\tdocker run --rm -v \"$(CURDIR):/input:ro\" -w /input "
                "$(LYCHEE_IMAGE) --no-progress --exclude '$(SELF_RELEASE_URL)' "
                "'./**/*.md'"
            ],
        )

    def test_repository_links_the_accompanying_arxiv_paper(self):
        readme = (ROOT / "README.md").read_text()
        for expected in (
            "## Accompanying paper",
            "https://arxiv.org/abs/2605.23059",
            "https://doi.org/10.48550/arXiv.2605.23059",
            "public, safety-bounded reference implementation",
            "reproducible virtual core",
            "cite the paper",
            "cite the software release",
        ):
            self.assertIn(expected, readme)
        self.assertNotIn("sites.google.com/view/cps-sec-2026", readme)
        self.assertNotIn("zenodo", readme.lower())

    def test_citation_prefers_the_arxiv_paper_without_claiming_a_software_doi(self):
        citation = (ROOT / "CITATION.cff").read_text()
        for expected in (
            'repository-code: "https://github.com/ylaung-uod/byot-cps"',
            'url: "https://github.com/ylaung-uod/byot-cps/releases/tag/v1.0.0"',
            "preferred-citation:",
            "type: article",
            'family-names: "Aung"',
            'given-names: "Yan Lin"',
            'family-names: "Neba"',
            'given-names: "Nelson Che"',
            'doi: "10.48550/arXiv.2605.23059"',
            'url: "https://arxiv.org/abs/2605.23059"',
        ):
            self.assertIn(expected, citation)
        self.assertFalse(any(line.startswith("doi:") for line in citation.splitlines()))
        self.assertNotIn("zenodo", citation.lower())


if __name__ == "__main__":
    unittest.main()
