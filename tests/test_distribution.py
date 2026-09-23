"""Regression tests for the public personal-workflows distribution."""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT / ".agents" / "plugins" / "marketplace.json"
PLUGIN_PATH = ROOT / "plugins" / "personal-workflows"
MANIFEST_PATH = PLUGIN_PATH / ".codex-plugin" / "plugin.json"
SECRET_SCANNER = ROOT / "scripts" / "scan_tracked_secrets.py"

EXPECTED_SKILLS = {
    "arch-compare",
    "arch-design",
    "arch-map",
    "code-review",
    "debug",
    "doc-analyze",
    "doc-estimate",
    "doc-ingest",
    "doc-summarize",
    "repository-audit",
    "spec-define",
    "spec-implement",
    "spec-plan",
}
EXPECTED_AGENTS = {
    "doc-analyst.toml",
    "document-worker.toml",
    "review-audit.toml",
    "review-quality.toml",
    "review-spec.toml",
}
EXPECTED_PUBLIC_METADATA = {
    "author": {"name": "Light2288", "url": "https://github.com/Light2288"},
    "license": "MIT",
    "repository": "https://github.com/Light2288/codex-bootstrapping",
    "keywords": ["codex", "superpowers", "workflows", "sdlc"],
}
LIKELY_CREDENTIAL_FILENAMES = {".env", ".env.local", "credentials", "credentials.json"}
LIKELY_CREDENTIAL_VALUE = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|"
    r"github_pat_[A-Za-z0-9_]{22,}|xox[bp]-[A-Za-z0-9-]{20,})\b"
)


class PublicDistributionTest(unittest.TestCase):
    def load_manifest(self):
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def load_marketplace(self):
        return json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))

    def run_secret_scanner(self, repository):
        return subprocess.run(
            [sys.executable, str(SECRET_SCANNER), "--root", str(repository)],
            check=False,
            capture_output=True,
            text=True,
            env=dict(os.environ, PATH="/usr/bin:/bin:/usr/sbin:/sbin"),
        )

    def test_marketplace_entry_resolves_to_the_public_plugin_manifest(self):
        marketplace = self.load_marketplace()
        manifest = self.load_manifest()

        self.assertEqual(marketplace["name"], "personal")
        self.assertEqual(
            marketplace["interface"],
            {"displayName": "Personal"},
        )
        self.assertEqual(len(marketplace["plugins"]), 1)
        self.assertEqual(
            marketplace["plugins"][0],
            {
                "name": manifest["name"],
                "source": {
                    "source": "local",
                    "path": "./plugins/personal-workflows",
                },
                "policy": {
                    "installation": "AVAILABLE",
                    "authentication": "ON_INSTALL",
                },
                "category": "Developer Tools",
            },
        )

    def test_manifest_has_the_version_and_public_metadata_consumers_need(self):
        manifest = self.load_manifest()

        self.assertEqual(manifest["name"], "personal-workflows")
        self.assertEqual(manifest["version"], "1.0.0")
        self.assertEqual(
            {key: manifest[key] for key in EXPECTED_PUBLIC_METADATA},
            EXPECTED_PUBLIC_METADATA,
        )
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertEqual(
            manifest["interface"],
            {
                "displayName": "Personal Workflows",
                "shortDescription": "Extend Superpowers with personal engineering workflows.",
                "longDescription": (
                    "Extends Superpowers with spec-driven SDLC, architecture, document, "
                    "and repository-audit workflows for Codex."
                ),
                "developerName": "Light2288",
                "category": "Productivity",
                "capabilities": [],
                "defaultPrompt": (
                    "Use Personal Workflows to extend Superpowers with spec-driven SDLC, "
                    "architecture, document, and repository-audit workflows."
                ),
            },
        )

    def test_distribution_contains_the_approved_skills_and_agents(self):
        skills = {
            path.name
            for path in (PLUGIN_PATH / "skills").iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        }
        agents = {
            path.name for path in (PLUGIN_PATH / "codex-agents").glob("*.toml")
        }

        self.assertEqual(skills, EXPECTED_SKILLS)
        self.assertEqual(agents, EXPECTED_AGENTS)

    def test_profile_check_mode_reports_changes_without_writing_a_codex_home(self):
        installer = PLUGIN_PATH / "scripts" / "install_profile.py"
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / "codex-home"

            result = subprocess.run(
                [
                    sys.executable,
                    str(installer),
                    "--codex-home",
                    str(codex_home),
                    "--check",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(result.stdout),
                {
                    "agents": {name: "would-create" for name in sorted(EXPECTED_AGENTS)},
                    "guidance": "would-update",
                },
            )
            self.assertFalse(codex_home.exists())

    def test_credential_detector_matches_likely_credential_values(self):
        values = (
            "sk-abcdefghijklmnopqrstuvwxyz123456",
            "ghp_abcdefghijklmnopqrstuvwxyz1234567890",
            "github_pat_abcdefghijklmnopqrstuvwxyz",
            "xoxb-1234567890-abcdefghijklmnopqrstuvwxyz",
        )

        for value in values:
            with self.subTest(value=value):
                self.assertIsNotNone(LIKELY_CREDENTIAL_VALUE.search(value))

    def test_tracked_secret_scan_includes_docs_without_printing_the_match(self):
        """Excluding public docs or echoing a match can publish or expose a credential."""
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            leak = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
            (repository / "docs").mkdir()
            (repository / "docs" / "leak.md").write_text(leak + "\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(repository)], check=True)
            subprocess.run(["git", "-C", str(repository), "add", "docs/leak.md"], check=True)

            result = self.run_secret_scanner(repository)

            output = result.stdout + result.stderr
            self.assertEqual(result.returncode, 1, output)
            self.assertIn("docs/leak.md:1", output)
            self.assertNotIn(leak, output)

    def test_tracked_secret_scan_allowlists_only_exact_detector_fixtures(self):
        """A broad test-file exception would hide a real credential beside detector fixtures."""
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            fixture_path = repository / "tests" / "test_distribution.py"
            fixture_path.parent.mkdir()
            intentional_fixtures = (
                "sk-abcdefghijklmnopqrstuvwxyz123456",
                "ghp_abcdefghijklmnopqrstuvwxyz1234567890",
                "github_pat_abcdefghijklmnopqrstuvwxyz",
                "xoxb-1234567890-abcdefghijklmnopqrstuvwxyz",
            )
            fixture_path.write_text("\n".join(intentional_fixtures) + "\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(repository)], check=True)
            subprocess.run(["git", "-C", str(repository), "add", "tests/test_distribution.py"], check=True)

            allowed = self.run_secret_scanner(repository)

            self.assertEqual(allowed.returncode, 0, allowed.stdout + allowed.stderr)

            unexpected = "sk-" + "abcdefghijklmnopqrstuvwxyz654321"
            fixture_path.write_text(
                fixture_path.read_text(encoding="utf-8") + unexpected + "\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(repository), "add", "tests/test_distribution.py"], check=True)

            rejected = self.run_secret_scanner(repository)

            output = rejected.stdout + rejected.stderr
            self.assertEqual(rejected.returncode, 1, output)
            self.assertIn("tests/test_distribution.py:5", output)
            self.assertNotIn(unexpected, output)

    def test_tracked_secret_scan_does_not_follow_symlinks_outside_the_repository(self):
        """Following a tracked symlink could make verification read machine-local state."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            repository = temporary / "repository"
            repository.mkdir()
            external = temporary / "machine-local"
            external.write_text("sk-" + "outside_repository_credential" + "\n", encoding="utf-8")
            (repository / "tracked-link").symlink_to(external)
            subprocess.run(["git", "init", "-q", str(repository)], check=True)
            subprocess.run(["git", "-C", str(repository), "add", "tracked-link"], check=True)

            result = self.run_secret_scanner(repository)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_distribution_declares_no_figma_integration_or_likely_credentials(self):
        json_paths = [MARKETPLACE_PATH, MANIFEST_PATH]
        for path in json_paths:
            with self.subTest(path=path):
                self.assertNotIn("figma", path.read_text(encoding="utf-8").lower())

        for path in PLUGIN_PATH.rglob("*"):
            if not path.is_file():
                continue
            with self.subTest(path=path):
                self.assertNotIn(path.name.lower(), LIKELY_CREDENTIAL_FILENAMES)
                content = path.read_text(encoding="utf-8", errors="ignore")
                self.assertIsNone(LIKELY_CREDENTIAL_VALUE.search(content))


if __name__ == "__main__":
    unittest.main()
