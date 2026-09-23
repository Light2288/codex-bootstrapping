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
        state_path = temporary / "marketplaces.json"
        fake_codex.write_text(
            "#!{python}\n"
            "import json\n"
            "import os\n"
            "import sys\n"
            "from pathlib import Path\n"
            "log = Path(os.environ['FAKE_CODEX_LOG'])\n"
            "with log.open('a', encoding='utf-8') as stream:\n"
            "    stream.write(json.dumps({{'args': sys.argv[1:], 'codex_home': os.environ.get('CODEX_HOME')}}) + '\\n')\n"
            "if sys.argv[1:] == ['plugin', 'marketplace', 'list', '--json']:\n"
            "    print(Path(os.environ['FAKE_MARKPLACES_PATH']).read_text(encoding='utf-8'))\n"
            "elif sys.argv[1:3] == ['plugin', 'marketplace'] and sys.argv[3] == 'add':\n"
            "    root = sys.argv[4]\n"
            "    Path(os.environ['FAKE_MARKPLACES_PATH']).write_text(json.dumps({{'marketplaces': [{{'name': 'personal', 'root': root, 'marketplaceSource': {{'source': 'local', 'path': root}}}}]}}), encoding='utf-8')\n"
            "sys.exit(0)\n".format(python=sys.executable),
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)
        if not state_path.exists():
            state_path.write_text("[]", encoding="utf-8")
        env = dict(
            os.environ,
            PATH=str(fake_bin) + os.pathsep + os.environ["PATH"],
            FAKE_CODEX_LOG=str(log),
            FAKE_MARKPLACES_PATH=str(state_path),
        )
        if environment:
            env.update(environment)
        if "FAKE_MARKETPLACES" in env:
            state_path.write_text(env["FAKE_MARKETPLACES"], encoding="utf-8")
        prior_lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        result = subprocess.run(
            ["zsh", str(SCRIPT), "--codex-home", str(temporary / "codex-home"), *arguments],
            check=False,
            capture_output=True,
            input=input_text,
            text=True,
            env=env,
        )
        calls = []
        homes = []
        if log.exists():
            entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()][len(prior_lines):]
            calls = [entry["args"] for entry in entries]
            homes = [entry["codex_home"] for entry in entries]
        return result, calls, homes

    def install_complete_profile(self, home, minified_superpowers=False):
        result = subprocess.run(
            [sys.executable, str(PROFILE_INSTALLER), "--codex-home", str(home), "--install"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        cache = home / "plugins" / "cache" / "openai-curated-remote"
        manifests = {
            "superpowers": '{"name":"superpowers"}' if minified_superpowers else json.dumps({"name": "superpowers"}),
            "personal-workflows": json.dumps({"name": "personal-workflows"}, indent=2),
        }
        for name, contents in manifests.items():
            manifest = cache / name / "1.0.0" / ".codex-plugin" / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(contents, encoding="utf-8")

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
                ["zsh", str(SCRIPT), "--codex-home", str(temporary / "codex-home"), "--dry-run"],
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

    def test_inspection_modes_do_not_write_a_codex_home_or_invoke_codex(self):
        """Inspection must not risk a Codex startup write in the caller's home."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            for mode in ("--check", "--dry-run"):
                with self.subTest(mode=mode):
                    result, calls, _ = self.run_bootstrap(temporary, mode)

                    self.assertEqual(result.returncode, 1 if mode == "--check" else 0, result.stderr)
                    self.assertFalse((temporary / "codex-home").exists())
                    self.assertEqual(calls, [])
                    self.assertIn("Superpowers: missing", result.stdout)
                    self.assertIn("personal-workflows: missing", result.stdout)

    def test_bootstrap_derives_the_repository_root_from_its_script_location(self):
        """Using the caller's directory would register the wrong marketplace after cd."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result, _, _ = self.run_bootstrap(temporary, "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(ROOT), result.stdout)

    def test_conflicting_personal_marketplace_is_refused_without_a_write(self):
        """Overwriting a same-named marketplace could replace another user's plugin source."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            result, calls, _ = self.run_bootstrap(
                temporary,
                input_text="y\n",
                environment={
                    "FAKE_MARKETPLACES": json.dumps(
                        {"marketplaces": [{"name": "personal", "root": "/unrelated/marketplace"}]}
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
            first, first_calls, first_homes = self.run_bootstrap(temporary, input_text="y\n")
            second, second_calls, second_homes = self.run_bootstrap(temporary, input_text="y\n")
            home = temporary / "codex-home"

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertTrue((home / "AGENTS.md").exists())
            self.assertEqual((home / "AGENTS.md").read_text(encoding="utf-8").count("<!-- personal-workflows:start -->"), 1)
            self.assertIn(["plugin", "marketplace", "add", str(ROOT)], first_calls)
            self.assertIn(["plugin", "add", "superpowers@openai-curated-remote"], first_calls)
            self.assertIn(["plugin", "add", "personal-workflows@personal"], first_calls)
            self.assertNotIn(["plugin", "marketplace", "add", str(ROOT)], second_calls)
            self.assertEqual(first_homes, [str(home)] * len(first_homes))
            self.assertEqual(second_homes, [str(home)] * len(second_homes))
            self.assertNotIn("configure-provider", first.stdout + first.stderr + second.stdout + second.stderr)
            self.assertTrue(PROFILE_INSTALLER.exists())

    def test_real_schema_registration_is_idempotent(self):
        """Ignoring root/marketplaceSource would re-add an already-correct marketplace."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            (temporary / "marketplaces.json").write_text(
                json.dumps(
                    {
                        "marketplaces": [
                            {
                                "name": "personal",
                                "root": str(ROOT),
                                "marketplaceSource": {"source": "local", "path": str(ROOT)},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result, calls, _ = self.run_bootstrap(temporary, input_text="y\n")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(["plugin", "marketplace", "add", str(ROOT)], calls)

    def test_check_accepts_a_complete_target_home_with_minified_and_pretty_manifests(self):
        """JSON formatting differences must not make a healthy installation fail."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            home = temporary / "codex-home"
            self.install_complete_profile(home, minified_superpowers=True)

            result, calls, _ = self.run_bootstrap(temporary, "--check")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(calls, [])
            self.assertIn("Superpowers: installed", result.stdout)
            self.assertIn("personal-workflows: installed", result.stdout)

    def test_check_rejects_drifted_guidance_or_agent_without_invoking_codex(self):
        """A success status despite changed managed files would hide a broken profile."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            home = temporary / "codex-home"
            self.install_complete_profile(home)
            agent = home / "agents" / "review-spec.toml"
            agent.write_text(agent.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")

            result, calls, _ = self.run_bootstrap(temporary, "--check")

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(calls, [])
            self.assertIn("Agent review-spec.toml: drift", result.stdout)

    def test_check_rejects_drifted_guidance_without_invoking_codex(self):
        """A changed marked guidance block must make the profile health check fail."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            home = temporary / "codex-home"
            self.install_complete_profile(home)
            guidance = home / "AGENTS.md"
            guidance.write_text(
                guidance.read_text(encoding="utf-8").replace(
                    "<!-- personal-workflows:start -->",
                    "<!-- personal-workflows:start -->\n# drift",
                ),
                encoding="utf-8",
            )

            result, calls, _ = self.run_bootstrap(temporary, "--check")

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(calls, [])
            self.assertIn("Guidance: drift", result.stdout)

    def test_check_rejects_a_malformed_cached_manifest_without_invoking_codex(self):
        """Treating invalid cache JSON as absent could conceal a corrupt plugin installation."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            home = temporary / "codex-home"
            self.install_complete_profile(home)
            manifest = home / "plugins" / "cache" / "openai-curated-remote" / "superpowers" / "1.0.0" / ".codex-plugin" / "plugin.json"
            manifest.write_text('{"name":', encoding="utf-8")

            result, calls, _ = self.run_bootstrap(temporary, "--check")

            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(calls, [])
            self.assertIn("Plugin cache: malformed manifest", result.stdout)


if __name__ == "__main__":
    unittest.main()
