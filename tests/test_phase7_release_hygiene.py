import unittest
from pathlib import Path

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
            "Commit attribution",
            "Hermes Agent <hermes-agent@localhost>",
        ):
            self.assertIn(expected, text)
        self.assertIn("44 links", text)
        self.assertNotIn("recorded in its GitHub pull request and release record", text)

    def test_release_process_requires_the_phase_seven_final_gate(self):
        checks = (ROOT / "docs" / "RELEASE-CHECKS.md").read_text()
        for expected in (
            "clean clone",
            "release archive",
            "annotated `v1.0.0` tag",
            "verified commit",
        ):
            self.assertIn(expected, checks)

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
