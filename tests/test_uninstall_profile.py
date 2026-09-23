"""Behavioral tests for safe personal-workflows profile removal."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "uninstall-profile.py"
PLUGIN = ROOT / "plugins" / "personal-workflows"
INSTALLER = PLUGIN / "scripts" / "install_profile.py"
MANAGED_HEADER = "# Managed by personal-workflows\n"


class UninstallProfileTest(unittest.TestCase):
    """These tests protect users' unrelated global agents and guidance."""

    def install_profile(self, home):
        result = subprocess.run(
            [sys.executable, str(INSTALLER), "--codex-home", str(home), "--install"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def run_uninstall(self, home, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--codex-home", str(home), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_uninstall_removes_only_installed_managed_agents_and_guidance(self):
        """Leaving managed files behind makes uninstall incomplete; deleting unrelated files loses user work."""
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex-home"
            self.install_profile(home)
            guidance = home / "AGENTS.md"
            guidance.write_text("user guidance\n" + guidance.read_text(encoding="utf-8"), encoding="utf-8")
            unrelated = home / "agents" / "custom.toml"
            unrelated.write_text("name = 'custom'\n", encoding="utf-8")

            result = self.run_uninstall(home, "--uninstall")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(guidance.read_text(encoding="utf-8"), "user guidance\n")
            self.assertTrue(unrelated.exists())
            self.assertEqual(list((home / "agents").glob("*.toml")), [unrelated])
            self.assertEqual(json.loads(result.stdout)["guidance"], "removed")

    def test_uninstall_refuses_an_unmanaged_agent_with_a_managed_filename(self):
        """Deleting a same-named user agent without the ownership marker is data loss."""
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex-home"
            agent = home / "agents" / "review-spec.toml"
            agent.parent.mkdir(parents=True)
            agent.write_text("name = 'user-owned'\n", encoding="utf-8")

            result = self.run_uninstall(home, "--uninstall")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to remove unmanaged agent", result.stderr)
            self.assertTrue(agent.exists())

    def test_check_reports_removals_without_writing(self):
        """A check mode that removes files cannot be used safely before uninstalling."""
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex-home"
            self.install_profile(home)
            original_guidance = (home / "AGENTS.md").read_text(encoding="utf-8")

            result = self.run_uninstall(home, "--check")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((home / "AGENTS.md").read_text(encoding="utf-8"), original_guidance)
            self.assertTrue((home / "agents" / "review-spec.toml").exists())
            report = json.loads(result.stdout)
            self.assertEqual(report["guidance"], "would-remove")
            self.assertIn("review-spec.toml", report["agents"])

    def test_uninstall_rejects_unmatched_guidance_markers(self):
        """Removing from an unmatched marker could erase user guidance after the marker."""
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "codex-home"
            home.mkdir()
            (home / "AGENTS.md").write_text("before\n<!-- personal-workflows:start -->\n", encoding="utf-8")

            result = self.run_uninstall(home, "--check")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("markers are unmatched", result.stderr)


if __name__ == "__main__":
    unittest.main()
