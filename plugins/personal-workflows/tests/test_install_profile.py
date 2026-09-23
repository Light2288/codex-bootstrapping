import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

from install_profile import (
    install_agent,
    install_profile,
    main as install_profile_main,
    merge_managed_block,
)


START = "<!-- personal-workflows:start -->"
END = "<!-- personal-workflows:end -->"
MANAGED = f"{START}\nnew managed guidance\n{END}\n"
AGENT_HEADER = "# Managed by personal-workflows\n"


class ProfileInstallerTest(unittest.TestCase):
    def run_installer(self, codex_home, *arguments):
        script = PLUGIN_ROOT / "scripts" / "install_profile.py"
        return subprocess.run(
            [
                sys.executable,
                str(script),
                "--codex-home",
                str(codex_home),
                *arguments,
            ],
            capture_output=True,
            text=True,
        )

    def test_merge_preserves_unmanaged_prefix_and_suffix(self):
        existing = f"before\n{START}\nold guidance\n{END}\nafter\n"

        merged = merge_managed_block(existing, MANAGED)

        self.assertEqual(merged, f"before\n{MANAGED}after\n")

    def test_merge_is_idempotent(self):
        existing = "unmanaged guidance\n"

        first_merge = merge_managed_block(existing, MANAGED)

        self.assertEqual(merge_managed_block(first_merge, MANAGED), first_merge)

    def test_merge_rejects_unmatched_or_duplicate_markers(self):
        with self.assertRaises(ValueError):
            merge_managed_block(f"{START}\nunmatched\n", MANAGED)
        with self.assertRaises(ValueError):
            merge_managed_block(f"{MANAGED}{MANAGED}", MANAGED)

    def test_agent_install_refuses_different_unmanaged_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.toml"
            destination = root / "destination.toml"
            source.write_text(f'{AGENT_HEADER}name = "managed"\n')
            destination.write_text('name = "unmanaged"\n')

            with self.assertRaises(FileExistsError):
                install_agent(source, destination, check_only=False)

            self.assertEqual(destination.read_text(), 'name = "unmanaged"\n')

    def test_agent_install_accepts_identical_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.toml"
            destination = root / "destination.toml"
            contents = f'{AGENT_HEADER}name = "managed"\n'
            source.write_text(contents)
            destination.write_text(contents)

            self.assertEqual(install_agent(source, destination, check_only=False), "unchanged")
            self.assertEqual(destination.read_text(), contents)

    def test_agent_install_replaces_existing_managed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.toml"
            destination = root / "destination.toml"
            source.write_text(f'{AGENT_HEADER}name = "updated"\n')
            destination.write_text(f'{AGENT_HEADER}name = "old"\n')

            self.assertEqual(install_agent(source, destination, check_only=False), "updated")
            self.assertEqual(destination.read_text(), source.read_text())

    def test_agent_install_refuses_marker_outside_ownership_header(self):
        hostile_contents = (
            f'name = "unmanaged"\n{AGENT_HEADER}description = "unrelated"\n',
            'name = "unmanaged"\n'
            'description = "mentions # Managed by personal-workflows in text"\n',
        )
        for contents in hostile_contents:
            with self.subTest(contents=contents):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    source = root / "source.toml"
                    destination = root / "destination.toml"
                    source.write_text(f'{AGENT_HEADER}name = "managed"\n')
                    destination.write_text(contents)

                    with self.assertRaises(FileExistsError):
                        install_agent(source, destination, check_only=False)

                    self.assertEqual(destination.read_text(), contents)

    def test_agent_install_accepts_exact_crlf_ownership_header(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.toml"
            destination = root / "destination.toml"
            source.write_text(f'{AGENT_HEADER}name = "updated"\n')
            destination.write_bytes(
                b'# Managed by personal-workflows\r\nname = "old"\r\n'
            )

            self.assertEqual(install_agent(source, destination, check_only=False), "updated")
            self.assertEqual(destination.read_text(), source.read_text())

    def test_check_mode_performs_no_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin_root = root / "plugin"
            (plugin_root / "profile").mkdir(parents=True)
            (plugin_root / "codex-agents").mkdir()
            (plugin_root / "profile" / "global-agents-block.md").write_text(MANAGED)
            (plugin_root / "codex-agents" / "review.toml").write_text(
                f'{AGENT_HEADER}name = "review"\n'
            )
            codex_home = root / "codex"
            codex_home.mkdir()
            agents_directory = codex_home / "agents"
            agents_file = codex_home / "AGENTS.md"
            agents_file.write_text("unmanaged guidance\n")

            report = install_profile(codex_home, plugin_root, check_only=True)

            self.assertEqual(report["guidance"], "would-update")
            self.assertEqual(report["agents"], {"review.toml": "would-create"})
            self.assertEqual(agents_file.read_text(), "unmanaged guidance\n")
            self.assertFalse(agents_directory.exists())

    def test_cli_explicit_install_writes_profile_to_selected_codex_home(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / "codex"

            result = self.run_installer(codex_home, "--install")

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["guidance"], "updated")
            self.assertIn(START, (codex_home / "AGENTS.md").read_text())
            source_agents = sorted((PLUGIN_ROOT / "codex-agents").glob("*.toml"))
            self.assertEqual(
                report["agents"],
                {source.name: "created" for source in source_agents},
            )
            for source in source_agents:
                self.assertEqual(
                    (codex_home / "agents" / source.name).read_text(),
                    source.read_text(),
                )

    def test_cli_rejects_install_and_check_together_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / "codex"

            result = self.run_installer(codex_home, "--install", "--check")

            self.assertEqual(result.returncode, 2)
            self.assertIn("not allowed with argument", result.stderr)
            self.assertFalse(codex_home.exists())

    def test_cli_requires_an_explicit_mode_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / "codex"

            result = self.run_installer(codex_home)

            self.assertEqual(result.returncode, 2)
            self.assertIn("one of the arguments --install --check is required", result.stderr)
            self.assertFalse(codex_home.exists())

    def test_cli_without_mode_does_not_target_the_default_codex_home(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            home.mkdir()

            with contextlib.redirect_stderr(io.StringIO()), patch(
                "install_profile.Path.home", return_value=home
            ), patch.object(sys, "argv", ["install_profile.py"]):
                with self.assertRaises(SystemExit) as result:
                    install_profile_main()

            self.assertEqual(result.exception.code, 2)
            self.assertFalse((home / ".codex").exists())

    def test_cli_explicit_install_backs_up_replaced_guidance_and_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            codex_home = Path(directory) / "codex"
            managed_agent = codex_home / "agents" / "review-spec.toml"
            original_guidance = f"before\n{START}\nold guidance\n{END}\nafter\n"
            original_agent = f'{AGENT_HEADER}name = "old-review-spec"\n'
            codex_home.mkdir()
            (codex_home / "AGENTS.md").write_text(original_guidance)
            managed_agent.parent.mkdir()
            managed_agent.write_text(original_agent)

            result = self.run_installer(codex_home, "--install")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(START, (codex_home / "AGENTS.md").read_text())
            self.assertEqual(
                managed_agent.read_text(),
                (PLUGIN_ROOT / "codex-agents" / "review-spec.toml").read_text(),
            )
            guidance_backups = list(codex_home.glob("AGENTS.md.backup.*"))
            agent_backups = list(managed_agent.parent.glob("review-spec.toml.backup.*"))
            self.assertEqual(len(guidance_backups), 1)
            self.assertEqual(len(agent_backups), 1)
            self.assertEqual(guidance_backups[0].read_text(), original_guidance)
            self.assertEqual(agent_backups[0].read_text(), original_agent)


if __name__ == "__main__":
    unittest.main()
