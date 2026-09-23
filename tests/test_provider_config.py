"""Behavioral tests for the safe custom-provider TOML transformer."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.provider_config import (
    DEFAULT_SETTINGS,
    ProviderSettings,
    ValidationError,
    atomic_write_config,
    merge_config,
    preview_config,
    validate_settings,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "provider_config.py"
WRAPPER = ROOT / "scripts" / "configure-provider.zsh"


class ProviderConfigTest(unittest.TestCase):
    """The tests name configuration errors that must be caught before writes."""

    def test_ibm_defaults_render_the_reviewed_keychain_provider_configuration(self):
        """Removing any reviewed default or changing its value is a bug."""
        rendered = merge_config("", DEFAULT_SETTINGS)

        self.assertEqual(
            rendered,
            'model = "gpt-5.6-sol"\n'
            'model_reasoning_effort = "high"\n'
            'model_provider = "ibm_ica"\n'
            "\n"
            "[model_providers.ibm_ica]\n"
            'name = "IBM ICA"\n'
            'base_url = "https://api.servicesessentials.ibm.com/v1"\n'
            'wire_api = "responses"\n'
            "supports_websockets = false\n"
            "\n"
            "[model_providers.ibm_ica.auth]\n"
            'command = "/usr/bin/security"\n'
            'args = ["find-generic-password", "-s", "codex-provider-ibm_ica", "-a", "codex", "-w"]\n'
            "timeout_ms = 5000\n"
            "refresh_interval_ms = 0\n",
        )

    def test_merge_preserves_unrelated_root_content_tables_and_comments(self):
        """Dropping a user-owned root key, table, or comment is a data-loss bug."""
        existing = (
            "# Keep this comment\n"
            'model = "old-model" # selected model\n'
            "approval_policy = \"on-request\"\n"
            "\n"
            "[mcp_servers.keep]\n"
            'command = "keep-me"\n'
        )

        rendered = merge_config(existing, DEFAULT_SETTINGS)

        self.assertIn("# Keep this comment\n", rendered)
        self.assertIn('approval_policy = "on-request"\n', rendered)
        self.assertIn("[mcp_servers.keep]\ncommand = \"keep-me\"\n", rendered)
        self.assertIn('model = "gpt-5.6-sol" # selected model\n', rendered)
        self.assertEqual(rendered.count("[model_providers.ibm_ica]"), 1)

    def test_merge_replaces_selected_provider_and_its_nested_auth_table(self):
        """Leaving stale provider auth behind can select the wrong credential source."""
        existing = (
            '[model_providers.ibm_ica]\n'
            'name = "Old IBM"\n'
            'env_key = "OLD_KEY"\n'
            "\n"
            "[model_providers.ibm_ica.auth]\n"
            'command = "/tmp/old-token"\n'
            "\n"
            "[model_providers.other]\n"
            'name = "Keep"\n'
        )

        rendered = merge_config(existing, DEFAULT_SETTINGS)

        self.assertNotIn("Old IBM", rendered)
        self.assertNotIn("OLD_KEY", rendered)
        self.assertNotIn("/tmp/old-token", rendered)
        self.assertIn('[model_providers.other]\nname = "Keep"\n', rendered)
        self.assertEqual(rendered.count("[model_providers.ibm_ica]"), 1)
        self.assertEqual(rendered.count("[model_providers.ibm_ica.auth]"), 1)

    def test_merge_escapes_toml_strings_without_using_input_as_toml_syntax(self):
        """An unescaped quote or backslash could turn a provider value into TOML syntax."""
        settings = ProviderSettings(
            provider_id="example",
            display_name='Example "Proxy" \\ east',
            base_url="https://provider.example/v1",
            model='model "alpha" \\ stable',
            reasoning_effort="medium",
            wire_api="responses",
            credential_env_var="EXAMPLE_KEY",
            supports_websockets=True,
            auth_mode="environment",
        )

        rendered = merge_config("", settings)

        self.assertIn('model = "model \\"alpha\\" \\\\ stable"\n', rendered)
        self.assertIn('name = "Example \\"Proxy\\" \\\\ east"\n', rendered)
        self.assertIn('env_key = "EXAMPLE_KEY"\n', rendered)
        self.assertIn("supports_websockets = true\n", rendered)

        if importlib.util.find_spec("tomllib") is not None:
            import tomllib

            parsed = tomllib.loads(rendered)
            self.assertEqual(parsed["model"], 'model "alpha" \\ stable')
            self.assertEqual(parsed["model_providers"]["example"]["name"], 'Example "Proxy" \\ east')

    def test_invalid_provider_values_are_rejected_before_a_merge(self):
        """Unsafe provider fields must not reach the configuration writer."""
        invalid_values = (
            {"provider_id": "wrong.id"},
            {"base_url": "not-a-url"},
            {"base_url": "ftp://provider.example/v1"},
            {"reasoning_effort": "turbo"},
            {"credential_env_var": "not-valid"},
            {"credential_env_var": "1STARTS_WITH_A_NUMBER"},
            {"wire_api": "chat"},
            {"auth_mode": "plaintext"},
        )

        for updates in invalid_values:
            with self.subTest(updates=updates):
                values = DEFAULT_SETTINGS.__dict__.copy()
                values.update(updates)
                with self.assertRaises(ValidationError):
                    validate_settings(ProviderSettings(**values))

    def test_websocket_setting_renders_both_boolean_values(self):
        """Inverting provider websocket support changes Codex transport behavior."""
        enabled_values = DEFAULT_SETTINGS.__dict__.copy()
        enabled_values["supports_websockets"] = True

        self.assertIn("supports_websockets = false\n", merge_config("", DEFAULT_SETTINGS))
        self.assertIn(
            "supports_websockets = true\n",
            merge_config("", ProviderSettings(**enabled_values)),
        )

    def test_environment_auth_and_keychain_auth_are_mutually_exclusive(self):
        """Combining env_key with command auth violates Codex's provider contract."""
        env_values = DEFAULT_SETTINGS.__dict__.copy()
        env_values["auth_mode"] = "environment"
        environment_config = merge_config("", ProviderSettings(**env_values))
        keychain_config = merge_config("", DEFAULT_SETTINGS)

        self.assertIn('env_key = "IBM_ICA_CODEX_API_KEY"\n', environment_config)
        self.assertNotIn("[model_providers.ibm_ica.auth]", environment_config)
        self.assertNotIn("env_key", keychain_config)
        self.assertIn("[model_providers.ibm_ica.auth]", keychain_config)
        self.assertNotIn("IBM_ICA_CODEX_API_KEY", keychain_config)

    def test_malformed_or_ambiguous_managed_content_fails_without_rendering(self):
        """Writing through ambiguous managed content risks changing the wrong provider."""
        malformed_inputs = (
            'model = "one"\nmodel = "two"\n',
            "[model_providers.ibm_ica\nname = \"broken\"\n",
            "[model_providers.ibm_ica]\nname = \"one\"\n[model_providers.ibm_ica]\nname = \"two\"\n",
        )

        for existing in malformed_inputs:
            with self.subTest(existing=existing):
                with self.assertRaises(ValidationError):
                    merge_config(existing, DEFAULT_SETTINGS)

    def test_merge_is_deterministic(self):
        """Changing output on repeat makes reviews and idempotent reruns unreliable."""
        initial = "# user comment\napproval_policy = \"on-request\"\n"
        first = merge_config(initial, DEFAULT_SETTINGS)

        self.assertEqual(merge_config(initial, DEFAULT_SETTINGS), first)
        self.assertEqual(merge_config(first, DEFAULT_SETTINGS), first)

    def test_preview_never_contains_a_secret_and_describes_the_storage_choice(self):
        """A preview that exposes a credential would leak it before confirmation."""
        preview = preview_config(DEFAULT_SETTINGS)

        self.assertIn("Credential storage: macOS Keychain", preview)
        self.assertIn("[model_providers.ibm_ica.auth]", preview)
        self.assertNotIn("example-test-secret", preview)
        self.assertNotIn("env_key", preview)

    def test_atomic_write_creates_a_backup_and_replaces_the_target(self):
        """Overwriting a configuration without a backup prevents safe recovery."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config.toml"
            target.write_text("old = true\n", encoding="utf-8")

            backup = atomic_write_config(target, 'model = "gpt-5.6-sol"\n')

            self.assertEqual(target.read_text(encoding="utf-8"), 'model = "gpt-5.6-sol"\n')
            self.assertIsNotNone(backup)
            self.assertEqual(backup.read_text(encoding="utf-8"), "old = true\n")

    def test_dry_run_cli_leaves_a_missing_target_absent(self):
        """A dry run that creates a config directory violates its no-write guarantee."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "new-home" / "config.toml"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--config", str(target), "--dry-run"],
                check=False,
                capture_output=True,
                text=True,
                env=dict(os.environ, CODEX_HOME=str(Path(directory) / "ignored-home")),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(target.parent.exists())
            self.assertIn("dry-run", result.stdout)

    def test_wrapper_check_and_dry_run_do_not_create_a_codex_home_or_echo_input(self):
        """Wrapper inspection modes must not create files or expose supplied input."""
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "new-home" / "config.toml"
            secret = "example-test-secret"
            for mode in ("--check", "--dry-run"):
                with self.subTest(mode=mode):
                    result = subprocess.run(
                        ["zsh", str(WRAPPER), "--config", str(target), mode],
                        check=False,
                        capture_output=True,
                        input=secret + "\n",
                        text=True,
                        env=dict(os.environ, CODEX_HOME=str(Path(directory) / "ignored-home")),
                    )

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertFalse(target.parent.exists())
                    self.assertNotIn(secret, result.stdout)
                    self.assertNotIn(secret, result.stderr)


if __name__ == "__main__":
    unittest.main()
