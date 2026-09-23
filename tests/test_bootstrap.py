"""Behavioral tests for the macOS Codex workflow bootstrap."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bootstrap-macos.zsh"
PROFILE_INSTALLER = ROOT / "plugins" / "personal-workflows" / "scripts" / "install_profile.py"


class BootstrapTest(unittest.TestCase):
    """Each test protects a user-visible bootstrap safety guarantee."""

    def run_bootstrap(self, temporary, *arguments, environment=None, input_text=""):
        fake_bin = temporary / "bin"
        fake_bin.mkdir(exist_ok=True)
        log = temporary / "codex-calls.jsonl"
        fake_codex = fake_bin / "codex"
        fake_codex.write_text(
            "#!{python}\n"
            "import json\n"
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n"
            "log = Path(os.environ['FAKE_CODEX_LOG'])\n"
            "with log.open('a', encoding='utf-8') as stream:\n"
            "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1:] == ['plugin', 'marketplace', 'list', '--json']:\n"
            "    print(os.environ.get('FAKE_MARKETPLACES', '[]'))\n"
            "sys.exit(0)\n".format(python=sys.executable),
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)
        env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ["PATH"], FAKE_CODEX_LOG=str(log))
        if environment:
            env.update(environment)
        result = subprocess.run(
            ["zsh", str(SCRIPT), "--codex-home", str(temporary / "codex-home"), *arguments],
            check=False,
            capture_output=True,
            input=input_text,
            text=True,
            env=env,
        )
        calls = []
        if log.exists():
            calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
        return result, calls

    def test_bundled_codex_is_used_when_path_and_override_are_absent(self):
        """Removing bundled discovery would make a bundled-only Codex install unusable."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            bundled = temporary / "ChatGPT.app" / "Contents" / "Resources" / "codex"
            bundled.parent.mkdir(parents=True)
            bundled.write_text(
                "#!/bin/zsh\n"
                "if [[ \"$*\" == \"plugin marketplace list --json\" ]]; then\n"
                "  print '[]'\n"
                "fi\n"
                "exit 0\n",
                encoding="utf-8",
            )
            bundled.chmod(0o755)
            result = subprocess.run(
                ["zsh", str(SCRIPT), "--codex-home", str(temporary / "codex-home"), "--check"],
                check=False,
                capture_output=True,
                text=True,
                env=dict(
                    os.environ,
                    PATH="/usr/bin:/bin:/usr/sbin:/sbin",
                    CODEX_BOOTSTRAP_BUNDLED_CODEX=str(bundled),
                ),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(bundled), result.stdout)

    def test_missing_codex_fails_with_official_installation_guidance(self):
        """Silently continuing without Codex would make the installer misleading."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result = subprocess.run(
                ["zsh", str(SCRIPT), "--codex-home", str(temporary / "codex-home"), "--check"],
                check=False,
                capture_output=True,
                text=True,
                env=dict(
                    os.environ,
                    PATH="/usr/bin:/bin:/usr/sbin:/sbin",
                    CODEX_BOOTSTRAP_BUNDLED_CODEX=str(temporary / "missing-codex"),
                ),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("https://developers.openai.com/codex/", result.stderr)

    def test_check_and_dry_run_do_not_write_a_codex_home_or_run_mutating_cli_commands(self):
        """Turning either inspection mode into an install would violate its safety contract."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            for mode in ("--check", "--dry-run"):
                with self.subTest(mode=mode):
                    result, calls = self.run_bootstrap(temporary, mode)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse((temporary / "codex-home").exists())
                    self.assertFalse(any(call[:3] == ["plugin", "marketplace", "add"] for call in calls))
                    self.assertFalse(any(call[:2] == ["plugin", "add"] for call in calls))

    def test_bootstrap_derives_the_repository_root_from_its_script_location(self):
        """Using the caller's directory would register the wrong marketplace after cd."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result, _ = self.run_bootstrap(temporary, "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(ROOT), result.stdout)

    def test_conflicting_personal_marketplace_is_refused_without_a_write(self):
        """Overwriting a same-named marketplace could replace another user's plugin source."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result, calls = self.run_bootstrap(
                temporary,
                "--check",
                environment={
                    "FAKE_MARKETPLACES": json.dumps(
                        [{"name": "personal", "path": "/unrelated/marketplace"}]
                    )
                },
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("conflicting marketplace", result.stderr)
            self.assertEqual(calls, [["plugin", "marketplace", "list", "--json"]])

    def test_confirmed_install_runs_the_explicit_profile_install_then_check_idempotently(self):
        """Skipping explicit install/check modes would make profile changes unsafe or unverifiable."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            first, first_calls = self.run_bootstrap(temporary, input_text="y\n")
            second, second_calls = self.run_bootstrap(temporary, input_text="y\n")
            home = temporary / "codex-home"

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertTrue((home / "AGENTS.md").exists())
            self.assertEqual((home / "AGENTS.md").read_text(encoding="utf-8").count("<!-- personal-workflows:start -->"), 1)
            self.assertIn(["plugin", "marketplace", "add", str(ROOT)], first_calls)
            self.assertIn(["plugin", "add", "personal-workflows@personal"], first_calls)
            self.assertNotIn("configure-provider", first.stdout + first.stderr + second.stdout + second.stderr)
            self.assertTrue(PROFILE_INSTALLER.exists())


if __name__ == "__main__":
    unittest.main()
