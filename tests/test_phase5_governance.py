import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PhaseFiveGovernanceTests(unittest.TestCase):
    def test_documentation_has_the_phase_five_reader_structure(self):
        readme = (ROOT / "README.md").read_text()
        for heading in ("Purpose", "Safety boundary", "Architecture", "Quick demonstration"):
            with self.subTest(heading=heading):
                self.assertRegex(readme, rf"(?m)^## {re.escape(heading)}$")
        for path in (
            "QUICKSTART.md",
            "docs/ARCHITECTURE.md",
            "docs/REPRODUCIBILITY.md",
            "docs/ARTIFACTS.md",
            "docs/SECURITY-BOUNDARY.md",
        ):
            with self.subTest(path=path):
                self.assertIn(f"]({path})", readme)
                self.assertTrue((ROOT / path).is_file())
        quickstart = (ROOT / "QUICKSTART.md").read_text()
        self.assertIn(
            "git clone https://github.com/ylaung-uod/BYOT-CPS.git byot-cps",
            quickstart,
        )
        self.assertIn("make prepare-images", quickstart)
        self.assertIn("make templates", quickstart)
        self.assertIn("make smoke-test", quickstart)

    def test_standard_public_project_files_are_present_and_actionable(self):
        required = (
            "CONTRIBUTING.md",
            "SECURITY.md",
            "CHANGELOG.md",
            "CITATION.cff",
            ".gitattributes",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            ".github/ISSUE_TEMPLATE/documentation.yml",
            ".github/ISSUE_TEMPLATE/config.yml",
            ".github/pull_request_template.md",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())

        contributing = (ROOT / "CONTRIBUTING.md").read_text()
        for expected in ("make test", "make phase4-verify", "Security reports", "operational malware"):
            self.assertIn(expected, contributing)

        security = (ROOT / "SECURITY.md").read_text()
        for expected in ("Supported versions", "private vulnerability", "Do not", "operational malware"):
            self.assertIn(expected, security)

        changelog = (ROOT / "CHANGELOG.md").read_text()
        self.assertIn("## [Unreleased]", changelog)
        self.assertIn("## [0.17.1]", changelog)

        citation = (ROOT / "CITATION.cff").read_text()
        for expected in ('cff-version: 1.2.0', 'title: "BYOT-CPS"', 'version: 1.0.0', 'license: MIT'):
            self.assertIn(expected, citation)

        attributes = (ROOT / ".gitattributes").read_text()
        self.assertIn("* text=auto", attributes)
        self.assertIn("*.sh text eol=lf", attributes)
        self.assertIn("*.qcow2 binary", attributes)

    def test_support_expectations_are_explicit(self):
        documentation = "\n".join(
            (ROOT / path).read_text()
            for path in (
                "README.md",
                "CONTRIBUTING.md",
                "SECURITY.md",
                "docs/SECURITY-BOUNDARY.md",
            )
        )
        normalized = re.sub(r"\s+", " ", documentation).lower()
        for expected in (
            "Ubuntu 22.04.5 LTS",
            "GNS3 2.2.55",
            "Docker 29.2.1",
            "QEMU 6.2.0",
            "Python 3.10.12",
            "reproducibility fixes",
            "private vulnerability",
            "do not support operational malware deployment",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected.lower(), normalized)


if __name__ == "__main__":
    unittest.main()
