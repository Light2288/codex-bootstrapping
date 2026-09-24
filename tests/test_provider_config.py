"""Behavioral tests for the safe custom-provider TOML transformer."""

import importlib.util
import builtins
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.provider_config as provider_config
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
PROFILE_INSTALLER = (
    ROOT / "plugins" / "personal-workflows" / "scripts" / "install_profile.py"
)


class ProviderConfigTest(unittest.TestCase):
    """The tests name configuration errors that must be caught before writes."""

    managed_agent_models = {
        "doc-analyst.toml": "gpt-5.6-sol",
        "document-worker.toml": "gpt-5.6-sol",
        "review-audit.toml": "gpt-5.6-sol",
        "review-quality.toml": "gpt-5.6-sol",
        "review-spec.toml": "gpt-5.6-luna",
    }

    def create_managed_codex_home(self, root):
        codex_home = root / "codex-home"
        agents = codex_home / "agents"
        plugin_cache = codex_home / "plugins" / "cache" / "sentinel"
        agents.mkdir(parents=True)
        plugin_cache.mkdir(parents=True)
        (plugin_cache / "untouched.txt").write_text("cache sentinel\n", encoding="utf-8")
        (codex_home / "config.toml").write_text(
            'model = "old-full"\n'
            'model_reasoning_effort = "high"\n'
            'model_provider = "ibm_ica"\n\n'
            '[model_providers.ibm_ica]\n'
            'name = "Keep Provider"\n'
            'base_url = "https://provider.example/v1"\n',
            encoding="utf-8",
        )
        (codex_home / "AGENTS.md").write_text(
            "unmanaged prefix\n"
            "<!-- personal-workflows:start -->\n"
            "## Managed model routing\n\n"
            "- `full`: `old-full`\n"
            "- `light`: `old-light`\n"
            "<!-- personal-workflows:end -->\n"
            "unmanaged suffix\n",
            encoding="utf-8",
        )
        for filename in self.managed_agent_models:
            name = filename[:-5]
            (agents / filename).write_text(
                "# Managed by personal-workflows\n"
                'name = "{0}"\n'
                'description = "keep {0}"\n'
                'model = "old-model"\n'
                'model_reasoning_effort = "high"\n'.format(name),
                encoding="utf-8",
            )
        return codex_home

    @staticmethod
    def tree_contents(root):
        return {
            path.relative_to(root): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
        }

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

    def test_merge_preserves_root_and_table_lookalikes_in_multiline_basic_strings(self):
        """Treating escaped quotes or string content as syntax can corrupt unrelated TOML."""
        multiline_value = (
            'notes = """\n'
            'model = "inside-basic"\n'
            '[model_providers.ibm_ica]\n'
            'escaped delimiter: \\"""\n'
            'model_provider = "still-inside"\n'
            '"""\n'
        )
        existing = multiline_value + 'model = "old-model"\n[mcp_servers.keep]\ncommand = "keep"\n'

        rendered = merge_config(existing, DEFAULT_SETTINGS)

        self.assertIn(multiline_value, rendered)
        self.assertIn('model = "gpt-5.6-sol"\n', rendered)
        self.assertIn('[mcp_servers.keep]\ncommand = "keep"\n', rendered)
        self.assertEqual(rendered.count("[model_providers.ibm_ica]"), 2)

    def test_merge_preserves_root_and_table_lookalikes_in_multiline_literal_strings(self):
        """Literal-string contents that resemble managed syntax must remain user-owned text."""
        multiline_value = (
            "notes = '''\n"
            'model_reasoning_effort = "inside-literal"\n'
            '[[model_providers.ibm_ica]]\n'
            "'''\n"
        )
        existing = multiline_value + 'model_reasoning_effort = "low"\n[tool.keep]\nenabled = true\n'

        rendered = merge_config(existing, DEFAULT_SETTINGS)

        self.assertIn(multiline_value, rendered)
        self.assertIn('model_reasoning_effort = "high"\n', rendered)
        self.assertIn('[tool.keep]\nenabled = true\n', rendered)
        self.assertEqual(rendered.count("[[model_providers.ibm_ica]]"), 1)

    def test_merge_replaces_quoted_managed_root_keys_without_adding_duplicates(self):
        """Ignoring quoted root keys creates duplicate semantic assignments in valid TOML."""
        existing = (
            '"model" = "old-model"\n'
            "'model_reasoning_effort' = \"medium\"\n"
            '"model_provider" = "other"\n'
        )

        rendered = merge_config(existing, DEFAULT_SETTINGS)

        self.assertIn('"model" = "gpt-5.6-sol"\n', rendered)
        self.assertIn("'model_reasoning_effort' = \"high\"\n", rendered)
        self.assertIn('"model_provider" = "ibm_ica"\n', rendered)
        self.assertNotIn('\nmodel = ', rendered)
        self.assertNotIn('\nmodel_reasoning_effort = ', rendered)
        self.assertNotIn('\nmodel_provider = ', rendered)

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

    def test_merge_preserves_unrelated_array_tables(self):
        """Rejecting a valid unrelated array table prevents safe configuration updates."""
        existing = '[[tool.rules]]\nname = "keep this rule"\n'

        rendered = merge_config(existing, DEFAULT_SETTINGS)

        self.assertIn(existing, rendered)
        self.assertIn("[model_providers.ibm_ica]", rendered)

    def test_merge_preserves_unrelated_toml_unicode_escape_headers(self):
        """Rejecting a valid TOML-only escape drops unrelated configuration access."""
        existing = '[tool."\\U0001F600"]\nname = "keep this table"\n'

        rendered = merge_config(existing, DEFAULT_SETTINGS)

        self.assertIn(existing, rendered)
        self.assertIn("[model_providers.ibm_ica]", rendered)

    def test_merge_replaces_a_quoted_selected_provider_header(self):
        """Missing a quoted managed header leaves duplicate semantic provider tables."""
        existing = (
            '[model_providers."ibm_ica"]\n'
            'name = "Old IBM"\n'
            'env_key = "OLD_KEY"\n'
        )

        rendered = merge_config(existing, DEFAULT_SETTINGS)

        self.assertNotIn("Old IBM", rendered)
        self.assertNotIn("OLD_KEY", rendered)
        self.assertNotIn('[model_providers."ibm_ica"]', rendered)
        self.assertEqual(rendered.count("[model_providers.ibm_ica]"), 1)

    def test_merge_replaces_a_toml_escaped_selected_provider_header(self):
        """Ignoring an escaped selected ID produces duplicate provider semantics."""
        existing = (
            '[model_providers."ibm\\U0000005fica"]\n'
            'name = "Old IBM"\n'
        )

        rendered = merge_config(existing, DEFAULT_SETTINGS)

        self.assertNotIn("Old IBM", rendered)
        self.assertNotIn('[model_providers."ibm\\U0000005fica"]', rendered)
        self.assertEqual(rendered.count("[model_providers.ibm_ica]"), 1)

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

    def test_reserved_codex_provider_ids_are_rejected_case_sensitively(self):
        """Replacing a built-in provider ID could corrupt Codex's reserved configuration."""
        for provider_id in ("openai", "ollama", "lmstudio"):
            with self.subTest(provider_id=provider_id):
                values = DEFAULT_SETTINGS.__dict__.copy()
                values["provider_id"] = provider_id
                with self.assertRaisesRegex(ValidationError, "reserved"):
                    validate_settings(ProviderSettings(**values))

        for provider_id in ("custom-provider_1", "OpenAI"):
            with self.subTest(provider_id=provider_id):
                values = DEFAULT_SETTINGS.__dict__.copy()
                values["provider_id"] = provider_id
                settings = ProviderSettings(**values)
                self.assertIs(validate_settings(settings), settings)

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

    def test_wrapper_rejects_reserved_provider_ids_before_credentials_or_config_writes(self):
        """Reserved IDs must fail at preview validation, before any credential side effect."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            target = temporary / "config.toml"
            helper_log = temporary / "keychain-helper-called"
            fake_helper = temporary / "fake-keychain-helper"
            original = 'approval_policy = "on-request"\n'
            target.write_text(original, encoding="utf-8")
            fake_helper.write_text(
                "#!{0}\n"
                "import os\n"
                "from pathlib import Path\n"
                "Path(os.environ['FAKE_HELPER_LOG']).write_text('called', encoding='utf-8')\n".format(
                    sys.executable
                ),
                encoding="utf-8",
            )
            fake_helper.chmod(0o755)

            for provider_id in ("openai", "ollama", "lmstudio"):
                with self.subTest(provider_id=provider_id):
                    result = subprocess.run(
                        ["zsh", str(WRAPPER), "--config", str(target)],
                        check=False,
                        capture_output=True,
                        input=provider_id + ("\n" * 9),
                        text=True,
                        env=dict(
                            os.environ,
                            CODEX_PROVIDER_KEYCHAIN_HELPER=str(fake_helper),
                            FAKE_HELPER_LOG=str(helper_log),
                        ),
                    )

                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("reserved", result.stderr)
                    self.assertNotIn("Apply this configuration?", result.stdout)
                    self.assertNotIn("API key", result.stdout)
                    self.assertFalse(helper_log.exists())
                    self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_wrapper_uses_keychain_helper_for_set_update_and_rollback(self):
        """Keychain writes must be stdin-only and compensated after config failure."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            state = temporary / "keychain-state"
            operations = temporary / "keychain-operations"
            arguments = temporary / "keychain-arguments"
            fake_helper = temporary / "fake-keychain-helper"
            fake_security = fake_bin / "security"
            fake_python = fake_bin / "python3"
            fake_wrapper = temporary / "configure-provider.zsh"
            target = temporary / "config.toml"
            target.write_text('approval_policy = "on-request"\n', encoding="utf-8")
            replacement = "new-test-credential"
            prior = "prior-test-credential"

            fake_helper.write_text(
                "#!{0}\n"
                "import os\n"
                "import sys\n"
                "from pathlib import Path\n"
                "state = Path(os.environ['FAKE_KEYCHAIN_STATE'])\n"
                "operation = sys.argv[1]\n"
                "open(os.environ['FAKE_KEYCHAIN_OPERATIONS'], 'a').write(operation + '\\n')\n"
                "open(os.environ['FAKE_KEYCHAIN_ARGUMENTS'], 'a').write('\\0'.join(sys.argv[1:]) + '\\n')\n"
                "if operation == 'check':\n"
                "    sys.exit(int(os.environ.get('FAKE_KEYCHAIN_CHECK_STATUS', '0')))\n"
                "if operation == 'get':\n"
                "    if not state.exists():\n"
                "        sys.exit(44)\n"
                "    sys.stdout.buffer.write(state.read_bytes())\n"
                "elif operation == 'set':\n"
                "    state.write_bytes(sys.stdin.buffer.read())\n"
                "elif operation == 'delete':\n"
                "    if state.exists():\n"
                "        state.unlink()\n"
                "else:\n"
                "    sys.exit(65)\n".format(sys.executable),
                encoding="utf-8",
            )
            fake_security.write_text(
                "#!{0}\nimport sys\nsys.stdin.buffer.read()\nsys.exit(44 if sys.argv[1] == 'find-generic-password' else 0)\n".format(
                    sys.executable
                ),
                encoding="utf-8",
            )
            fake_python.write_text(
                "#!{0}\nimport os\nimport sys\nsys.exit(0 if '--dry-run' in sys.argv else int(os.environ.get('FAKE_TRANSFORMER_STATUS', '0')))\n".format(
                    sys.executable
                ),
                encoding="utf-8",
            )
            for path in (fake_helper, fake_security, fake_python):
                path.chmod(0o755)
            wrapper_source = WRAPPER.read_text(encoding="utf-8")
            wrapper_source = wrapper_source.replace(
                'transformer="$script_dir/provider_config.py"',
                'transformer="{0}"'.format(SCRIPT),
            )
            fake_wrapper.write_text(
                wrapper_source.replace("/usr/bin/security", str(fake_security)),
                encoding="utf-8",
            )

            scenarios = (
                ("initial", None, 0, replacement),
                ("update", prior, 0, replacement),
                ("restore", prior, 42, prior),
                ("delete", None, 42, None),
            )
            for name, previous, transformer_status, expected in scenarios:
                with self.subTest(name=name):
                    for path in (state, operations, arguments):
                        if path.exists():
                            path.unlink()
                    if previous is not None:
                        state.write_text(previous, encoding="utf-8")
                    result = subprocess.run(
                        ["zsh", str(fake_wrapper), "--config", str(target)],
                        check=False,
                        capture_output=True,
                        input=("\n" * 9) + "y\n" + replacement + "\n",
                        text=True,
                        env=dict(
                            os.environ,
                            PATH=str(fake_bin) + os.pathsep + os.environ["PATH"],
                            CODEX_PROVIDER_KEYCHAIN_HELPER=str(fake_helper),
                            FAKE_KEYCHAIN_STATE=str(state),
                            FAKE_KEYCHAIN_OPERATIONS=str(operations),
                            FAKE_KEYCHAIN_ARGUMENTS=str(arguments),
                            FAKE_TRANSFORMER_STATUS=str(transformer_status),
                        ),
                    )

                    self.assertEqual(
                        result.returncode,
                        transformer_status,
                        (result.stdout, result.stderr),
                    )
                    self.assertNotIn(replacement, result.stdout)
                    self.assertNotIn(replacement, result.stderr)
                    self.assertTrue(operations.exists())
                    self.assertNotIn(replacement, arguments.read_text(encoding="utf-8"))
                    self.assertIn("set", operations.read_text(encoding="utf-8").splitlines())
                    if expected is None:
                        self.assertFalse(state.exists())
                    else:
                        self.assertEqual(
                            hashlib.sha256(state.read_bytes()).hexdigest(),
                            hashlib.sha256(expected.encode("utf-8")).hexdigest(),
                        )

    def test_wrapper_stops_when_keychain_helper_cannot_load(self):
        """A failed helper check must prevent credential and config mutation."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            fake_helper = temporary / "fake-keychain-helper"
            fake_security = fake_bin / "security"
            fake_python = fake_bin / "python3"
            fake_wrapper = temporary / "configure-provider.zsh"
            target = temporary / "config.toml"
            target.write_text('approval_policy = "on-request"\n', encoding="utf-8")
            fake_helper.write_text("#!{0}\nimport sys\nsys.exit(71)\n".format(sys.executable), encoding="utf-8")
            fake_security.write_text("#!{0}\nimport sys\nsys.exit(0)\n".format(sys.executable), encoding="utf-8")
            fake_python.write_text("#!{0}\nimport sys\nsys.exit(0)\n".format(sys.executable), encoding="utf-8")
            for path in (fake_helper, fake_security, fake_python):
                path.chmod(0o755)
            wrapper_source = WRAPPER.read_text(encoding="utf-8")
            wrapper_source = wrapper_source.replace(
                'transformer="$script_dir/provider_config.py"',
                'transformer="{0}"'.format(SCRIPT),
            )
            fake_wrapper.write_text(
                wrapper_source.replace("/usr/bin/security", str(fake_security)),
                encoding="utf-8",
            )

            result = subprocess.run(
                ["zsh", str(fake_wrapper), "--config", str(target)],
                check=False,
                capture_output=True,
                input=("\n" * 9) + "y\n",
                text=True,
                env=dict(
                    os.environ,
                    PATH=str(fake_bin) + os.pathsep + os.environ["PATH"],
                    CODEX_PROVIDER_KEYCHAIN_HELPER=str(fake_helper),
                ),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Keychain helper", result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), 'approval_policy = "on-request"\n')

    def test_credential_only_replaces_keychain_secret_without_changing_codex_files(self):
        """A focused credential rotation must not rewrite provider or routing configuration."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            codex_home = self.create_managed_codex_home(temporary)
            before = self.tree_contents(codex_home)
            state = temporary / "keychain-state"
            operations = temporary / "keychain-operations"
            arguments = temporary / "keychain-arguments"
            helper = temporary / "fake-keychain-helper"
            secret = "focused-secret-value"
            helper.write_text(
                "#!{0}\n"
                "import os\n"
                "import sys\n"
                "from pathlib import Path\n"
                "state = Path(os.environ['FAKE_KEYCHAIN_STATE'])\n"
                "operation = sys.argv[1]\n"
                "open(os.environ['FAKE_KEYCHAIN_OPERATIONS'], 'a').write(operation + '\\n')\n"
                "open(os.environ['FAKE_KEYCHAIN_ARGUMENTS'], 'a').write('\\0'.join(sys.argv[1:]) + '\\n')\n"
                "if operation == 'check': sys.exit(0)\n"
                "if operation == 'get': sys.exit(44)\n"
                "if operation == 'set': state.write_bytes(sys.stdin.buffer.read())\n"
                "if operation == 'delete' and state.exists(): state.unlink()\n".format(sys.executable),
                encoding="utf-8",
            )
            helper.chmod(0o755)

            result = subprocess.run(
                ["zsh", str(WRAPPER), "--credential-only"],
                check=False,
                capture_output=True,
                input="\ny\n{0}\n".format(secret),
                text=True,
                env=dict(
                    os.environ,
                    CODEX_HOME=str(codex_home),
                    CODEX_PROVIDER_KEYCHAIN_HELPER=str(helper),
                    FAKE_KEYCHAIN_STATE=str(state),
                    FAKE_KEYCHAIN_OPERATIONS=str(operations),
                    FAKE_KEYCHAIN_ARGUMENTS=str(arguments),
                ),
            )

            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertEqual(self.tree_contents(codex_home), before)
            self.assertEqual(state.read_text(encoding="utf-8"), secret)
            self.assertEqual(
                operations.read_text(encoding="utf-8").splitlines(),
                ["check", "set"],
            )
            self.assertNotIn(secret, arguments.read_text(encoding="utf-8"))
            self.assertNotIn(secret, result.stdout)
            self.assertNotIn(secret, result.stderr)

    def test_models_only_updates_exact_owned_targets_with_backups_and_no_keychain(self):
        """Wrong role mapping or broad writes would silently route work to the wrong model."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            codex_home = self.create_managed_codex_home(temporary)
            before = self.tree_contents(codex_home)
            helper_log = temporary / "helper-called"
            helper = temporary / "fake-keychain-helper"
            helper.write_text(
                "#!{0}\nfrom pathlib import Path\nPath({1!r}).write_text('called')\n".format(
                    sys.executable, str(helper_log)
                ),
                encoding="utf-8",
            )
            helper.chmod(0o755)

            result = subprocess.run(
                ["zsh", str(WRAPPER), "--models-only"],
                check=False,
                capture_output=True,
                input="\n\ny\n",
                text=True,
                env=dict(
                    os.environ,
                    CODEX_HOME=str(codex_home),
                    CODEX_PROVIDER_KEYCHAIN_HELPER=str(helper),
                ),
            )

            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertFalse(helper_log.exists())
            config = (codex_home / "config.toml").read_text(encoding="utf-8")
            self.assertIn('model = "gpt-5.6-sol"\n', config)
            self.assertIn('base_url = "https://provider.example/v1"\n', config)
            guidance = (codex_home / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("unmanaged prefix\n", guidance)
            self.assertIn("unmanaged suffix\n", guidance)
            self.assertIn("- `full`: `gpt-5.6-sol`\n", guidance)
            self.assertIn("- `light`: `gpt-5.6-luna`\n", guidance)
            for filename, expected_model in self.managed_agent_models.items():
                with self.subTest(filename=filename):
                    contents = (codex_home / "agents" / filename).read_text(encoding="utf-8")
                    self.assertIn('model = "{0}"\n'.format(expected_model), contents)
                    backups = list((codex_home / "agents").glob(filename + ".backup.*"))
                    self.assertEqual(len(backups), 1)
                    self.assertEqual(backups[0].read_bytes(), before[Path("agents") / filename])
            for relative in (Path("config.toml"), Path("AGENTS.md")):
                backups = list((codex_home / relative.parent).glob(relative.name + ".backup.*"))
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_bytes(), before[relative])
            self.assertEqual(
                (codex_home / "plugins" / "cache" / "sentinel" / "untouched.txt").read_text(
                    encoding="utf-8"
                ),
                "cache sentinel\n",
            )

    def test_focused_modes_are_mutually_exclusive_before_any_mutation(self):
        """Selecting two focused modes must fail rather than choose an unsafe implicit order."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            codex_home = self.create_managed_codex_home(temporary)
            before = self.tree_contents(codex_home)
            result = subprocess.run(
                [
                    "zsh",
                    str(WRAPPER),
                    "--credential-only",
                    "--models-only",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=dict(os.environ, CODEX_HOME=str(codex_home)),
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("cannot be combined", result.stderr)
            self.assertEqual(self.tree_contents(codex_home), before)

    def test_focused_modes_reject_smoke_test_before_any_side_effect(self):
        """Accepting a focused smoke test while ignoring it misstates the requested run."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            codex_home = self.create_managed_codex_home(temporary)
            before = self.tree_contents(codex_home)
            helper_log = temporary / "keychain-helper-called"
            helper = temporary / "fake-keychain-helper"
            helper.write_text(
                "#!{0}\nfrom pathlib import Path\nPath({1!r}).write_text('called')\n".format(
                    sys.executable, str(helper_log)
                ),
                encoding="utf-8",
            )
            helper.chmod(0o755)

            for focused_mode in ("--credential-only", "--models-only"):
                with self.subTest(focused_mode=focused_mode):
                    result = subprocess.run(
                        ["zsh", str(WRAPPER), focused_mode, "--smoke-test"],
                        check=False,
                        capture_output=True,
                        text=True,
                        env=dict(
                            os.environ,
                            CODEX_HOME=str(codex_home),
                            CODEX_PROVIDER_KEYCHAIN_HELPER=str(helper),
                        ),
                    )

                    self.assertEqual(result.returncode, 2)
                    self.assertIn("--smoke-test", result.stderr)
                    self.assertEqual(self.tree_contents(codex_home), before)
                    self.assertFalse(helper_log.exists())

    def test_models_only_honors_the_exact_config_filename(self):
        """Replacing config.toml when --config named another file is a data-loss bug."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            codex_home = self.create_managed_codex_home(temporary)
            selected = codex_home / "alternate.toml"
            selected.write_bytes((codex_home / "config.toml").read_bytes())
            decoy = codex_home / "config.toml"
            decoy_before = decoy.read_bytes()

            result = subprocess.run(
                [
                    "zsh",
                    str(WRAPPER),
                    "--config",
                    str(selected),
                    "--models-only",
                ],
                check=False,
                capture_output=True,
                input="supported-full\nsupported-light\ny\n",
                text=True,
                env=dict(os.environ, CODEX_HOME=str(temporary / "ignored-home")),
            )

            self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
            self.assertIn('model = "supported-full"\n', selected.read_text(encoding="utf-8"))
            self.assertEqual(decoy.read_bytes(), decoy_before)
            self.assertTrue(list(codex_home.glob("alternate.toml.backup.*")))
            self.assertFalse(list(codex_home.glob("config.toml.backup.*")))

    def test_models_only_overrides_survive_profile_check_and_reinstall(self):
        """A supported routing override must not become profile drift on reinstall."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            codex_home = temporary / "codex-home"
            initial_install = subprocess.run(
                [
                    sys.executable,
                    str(PROFILE_INSTALLER),
                    "--codex-home",
                    str(codex_home),
                    "--install",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(initial_install.returncode, 0, initial_install.stderr)
            (codex_home / "config.toml").write_text(
                'model = "packaged-full"\nmodel_provider = "ibm_ica"\n',
                encoding="utf-8",
            )
            cache_sentinel = codex_home / "plugins" / "cache" / "sentinel.txt"
            cache_sentinel.parent.mkdir(parents=True)
            cache_sentinel.write_text("unchanged\n", encoding="utf-8")

            update = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--config",
                    str(codex_home / "config.toml"),
                    "--models-only",
                    "--full-model",
                    "supported-full",
                    "--light-model",
                    "supported-light",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(update.returncode, 0, (update.stdout, update.stderr))

            check = subprocess.run(
                [
                    sys.executable,
                    str(PROFILE_INSTALLER),
                    "--codex-home",
                    str(codex_home),
                    "--check",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(check.returncode, 0, check.stderr)
            check_report = json.loads(check.stdout)
            self.assertEqual(check_report["guidance"], "unchanged")
            self.assertTrue(
                all(status == "unchanged" for status in check_report["agents"].values())
            )

            reinstall = subprocess.run(
                [
                    sys.executable,
                    str(PROFILE_INSTALLER),
                    "--codex-home",
                    str(codex_home),
                    "--install",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(reinstall.returncode, 0, reinstall.stderr)
            self.assertIn(
                "- `full`: `supported-full`",
                (codex_home / "AGENTS.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                'model = "supported-light"',
                (codex_home / "agents" / "review-spec.toml").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertIn(
                'model = "supported-full"',
                (codex_home / "agents" / "review-quality.toml").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertEqual(cache_sentinel.read_text(encoding="utf-8"), "unchanged\n")

    def test_models_only_refuses_unmanaged_or_malformed_targets_without_partial_writes(self):
        """Ownership or structure ambiguity must stop the transaction before the first backup."""
        mutations = {
            "malformed-config-value": lambda home: (home / "config.toml").write_text(
                'model = "unterminated\n', encoding="utf-8"
            ),
            "unmanaged-agent": lambda home: (home / "agents" / "review-audit.toml").write_text(
                'name = "review-audit"\nmodel = "user-choice"\n', encoding="utf-8"
            ),
            "malformed-agent-table": lambda home: (
                home / "agents" / "review-audit.toml"
            ).write_text(
                "# Managed by personal-workflows\n"
                'name = "review-audit"\n'
                'model = "old-model"\n'
                "[broken\n",
                encoding="utf-8",
            ),
            "malformed-guidance": lambda home: (home / "AGENTS.md").write_text(
                "<!-- personal-workflows:start -->\n"
                "- `full`: `one`\n"
                "- `full`: `two`\n"
                "- `light`: `light`\n"
                "<!-- personal-workflows:end -->\n",
                encoding="utf-8",
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                codex_home = self.create_managed_codex_home(Path(directory))
                mutate(codex_home)
                before = self.tree_contents(codex_home)

                result = subprocess.run(
                    ["zsh", str(WRAPPER), "--models-only"],
                    check=False,
                    capture_output=True,
                    input="\n\n",
                    text=True,
                    env=dict(os.environ, CODEX_HOME=str(codex_home)),
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(
                    "managed" in result.stderr.lower()
                    or "personal-workflows" in result.stderr.lower(),
                    result.stderr,
                )
                self.assertEqual(self.tree_contents(codex_home), before)
                self.assertFalse(list(codex_home.rglob("*.backup.*")))

    def test_models_only_rolls_back_every_written_target_after_atomic_replace_failure(self):
        """A failure after one replacement must not leave model roles split across files."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            before = self.tree_contents(codex_home)
            real_exchange = provider_config._exchange_paths_at
            calls = {"count": 0}

            def fail_third_exchange(directory_descriptor, first, second):
                calls["count"] += 1
                if calls["count"] == 3:
                    raise OSError("injected atomic replacement failure")
                return real_exchange(directory_descriptor, first, second)

            with patch.object(
                provider_config,
                "_exchange_paths_at",
                side_effect=fail_third_exchange,
            ):
                with self.assertRaises(OSError):
                    provider_config.apply_model_routing_update(
                        codex_home,
                        "gpt-5.6-sol",
                        "gpt-5.6-luna",
                    )

            after = self.tree_contents(codex_home)
            for relative, contents in before.items():
                self.assertEqual(after[relative], contents, relative)
            self.assertEqual(len(list(codex_home.rglob("*.backup.*"))), 7)

    def test_models_only_does_not_overwrite_an_exact_target_swapped_after_verification(self):
        """A same-directory target swap after verification must survive unchanged."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            target = (codex_home / "config.toml").resolve()
            moved_original = codex_home / "config.original"
            unexpected = b'model = "external-owner"\n'
            real_open = provider_config._open_verified_file_at
            target_opens = {"count": 0}
            swapped = {"done": False}

            def open_then_swap(directory_descriptor, state):
                descriptor = real_open(directory_descriptor, state)
                if state.path == target:
                    target_opens["count"] += 1
                    if target_opens["count"] == 2:
                        target.rename(moved_original)
                        target.write_bytes(unexpected)
                        swapped["done"] = True
                return descriptor

            with patch.object(
                provider_config,
                "_open_verified_file_at",
                side_effect=open_then_swap,
            ):
                with self.assertRaises((ValidationError, OSError)):
                    provider_config.apply_model_routing_update(
                        codex_home,
                        "gpt-5.6-sol",
                        "gpt-5.6-luna",
                    )

            self.assertTrue(swapped["done"])
            self.assertEqual(target.read_bytes(), unexpected)
            self.assertTrue(moved_original.exists())

    def test_models_only_does_not_overwrite_an_exact_target_edited_after_verification(self):
        """An in-place edit after verification must survive the attempted exchange."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            target = (codex_home / "config.toml").resolve()
            unexpected = b'model = "external-in-place-edit"\n'
            real_open = provider_config._open_verified_file_at
            target_opens = {"count": 0}
            edited = {"done": False}

            def open_then_edit(directory_descriptor, state):
                descriptor = real_open(directory_descriptor, state)
                if state.path == target:
                    target_opens["count"] += 1
                    if target_opens["count"] == 2:
                        target.write_bytes(unexpected)
                        edited["done"] = True
                return descriptor

            with patch.object(
                provider_config,
                "_open_verified_file_at",
                side_effect=open_then_edit,
            ):
                with self.assertRaises((ValidationError, OSError)):
                    provider_config.apply_model_routing_update(
                        codex_home,
                        "gpt-5.6-sol",
                        "gpt-5.6-luna",
                    )

            self.assertTrue(edited["done"])
            self.assertEqual(target.read_bytes(), unexpected)

    def test_models_only_rollback_preserves_an_exact_target_edited_after_replacement(self):
        """Rollback must not overwrite content edited after this transaction replaced it."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            target = codex_home / "config.toml"
            external_edit = b'model = "external-post-replacement-edit"\n'
            real_replace = provider_config._atomic_replace_content_at
            replacements = {"count": 0}

            def edit_first_then_fail_second(directory_descriptor, state, content):
                replacements["count"] += 1
                if replacements["count"] == 2:
                    raise OSError("injected later replacement failure")
                result = real_replace(directory_descriptor, state, content)
                if replacements["count"] == 1:
                    target.write_bytes(external_edit)
                return result

            with patch.object(
                provider_config,
                "_atomic_replace_content_at",
                side_effect=edit_first_then_fail_second,
            ):
                with self.assertRaises(OSError):
                    provider_config.apply_model_routing_update(
                        codex_home,
                        "gpt-5.6-sol",
                        "gpt-5.6-luna",
                    )

            self.assertEqual(target.read_bytes(), external_edit)
            lock = codex_home / ".provider-model-routing.lock"
            journal = codex_home / ".provider-model-routing.journal"
            self.assertTrue(lock.exists())
            self.assertEqual(lock.read_bytes(), b"")
            self.assertTrue(journal.exists())
            self.assertTrue(journal.read_bytes())

    def test_models_only_recovers_an_empty_stale_lock_before_updating(self):
        """An unheld empty legacy lock must not require blind manual deletion."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            lock = codex_home / ".provider-model-routing.lock"
            lock.touch(mode=0o600)

            provider_config.apply_model_routing_update(
                codex_home,
                "recovered-full",
                "recovered-light",
            )

            self.assertTrue(lock.exists())
            self.assertEqual(lock.read_bytes(), b"")
            self.assertFalse((codex_home / ".provider-model-routing.journal").exists())
            self.assertIn(
                'model = "recovered-full"',
                (codex_home / "config.toml").read_text(encoding="utf-8"),
            )

    def test_models_only_migrates_a_nonempty_legacy_lock_journal(self):
        """Upgrading must not discard recovery metadata stored in the old lock file."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            lock = codex_home / ".provider-model-routing.lock"
            legacy = {
                "version": 1,
                "transaction_id": "legacy-interrupted",
                "owner": {"pid": 999999},
                "phase": "recovery-required",
                "targets": [
                    {
                        "path": "config.toml",
                        "backup": None,
                        "original_sha256": "0" * 64,
                        "desired_sha256": "1" * 64,
                        "mode": 0o600,
                        "parent_identity": [],
                        "installed_identity": None,
                        "displaced": None,
                    }
                ],
            }
            lock.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
            target = codex_home / "config.toml"
            before = target.read_bytes()

            with self.assertRaisesRegex(ValidationError, "lacks a recovery backup"):
                provider_config.apply_model_routing_update(
                    codex_home,
                    "recovered-full",
                    "recovered-light",
                )

            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(lock.read_bytes(), b"")
            journal = codex_home / ".provider-model-routing.journal"
            envelope = json.loads(journal.read_text(encoding="utf-8"))
            self.assertEqual(envelope["payload"]["transaction_id"], "legacy-interrupted")

    def test_models_only_rejects_a_corrupted_atomic_journal(self):
        """A corrupt recovery journal must never be mistaken for no transaction."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            lock = codex_home / ".provider-model-routing.lock"
            lock.touch(mode=0o600)
            journal = codex_home / ".provider-model-routing.journal"
            corrupt = {
                "journal_version": 1,
                "payload": {
                    "version": 1,
                    "transaction_id": "interrupted",
                    "owner": {"pid": 999999},
                    "phase": "backups",
                    "targets": [],
                },
                "sha256": "0" * 64,
            }
            journal.write_text(json.dumps(corrupt) + "\n", encoding="utf-8")
            before = self.tree_contents(codex_home)

            with self.assertRaisesRegex(ValidationError, "checksum"):
                provider_config.apply_model_routing_update(
                    codex_home,
                    "recovered-full",
                    "recovered-light",
                )

            self.assertEqual(self.tree_contents(codex_home), before)

    def test_models_only_preserves_conflicting_legacy_and_atomic_journals(self):
        """Migration must not truncate malformed or conflicting legacy recovery state."""
        cases = {
            "malformed": b"{not-json\n",
            "mismatched": None,
        }
        for name, legacy_bytes in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                codex_home = self.create_managed_codex_home(Path(directory))
                lock = codex_home / ".provider-model-routing.lock"
                payload = {
                    "version": 1,
                    "transaction_id": "atomic-record",
                    "owner": {"pid": 999999},
                    "phase": "backups",
                    "targets": [],
                }
                canonical = json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                envelope = {
                    "journal_version": 1,
                    "payload": payload,
                    "sha256": hashlib.sha256(canonical).hexdigest(),
                }
                journal = codex_home / ".provider-model-routing.journal"
                journal.write_text(json.dumps(envelope) + "\n", encoding="utf-8")
                if legacy_bytes is None:
                    conflicting = dict(payload, transaction_id="legacy-record")
                    legacy_bytes = (json.dumps(conflicting) + "\n").encode("utf-8")
                lock.write_bytes(legacy_bytes)
                target = codex_home / "config.toml"
                target_before = target.read_bytes()
                journal_before = journal.read_bytes()

                with self.assertRaises(ValidationError):
                    provider_config.apply_model_routing_update(
                        codex_home,
                        "recovered-full",
                        "recovered-light",
                    )

                self.assertEqual(lock.read_bytes(), legacy_bytes)
                self.assertEqual(journal.read_bytes(), journal_before)
                self.assertEqual(target.read_bytes(), target_before)

    def test_models_only_preserves_a_corrupted_journal_at_final_cleanup(self):
        """Cleanup must not delete journal evidence changed after the last publish."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            journal = codex_home / ".provider-model-routing.journal"
            external = b"externally-corrupted-journal\n"
            real_remove = provider_config._remove_journal_at

            def corrupt_then_remove(directory_descriptor, *arguments):
                journal.write_bytes(external)
                return real_remove(directory_descriptor, *arguments)

            with patch.object(
                provider_config,
                "_remove_journal_at",
                side_effect=corrupt_then_remove,
            ):
                with self.assertRaises(ValidationError):
                    provider_config.apply_model_routing_update(
                        codex_home,
                        "recovered-full",
                        "recovered-light",
                    )

            self.assertEqual(journal.read_bytes(), external)

    def test_models_only_preserves_a_journal_swapped_during_cleanup(self):
        """Cleanup exchange must not unlink a journal swapped after verification."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            journal = codex_home / ".provider-model-routing.journal"
            external = b"external-journal-after-cleanup-exchange\n"
            real_exchange = provider_config._exchange_paths_at
            swapped = {"done": False}

            def exchange_then_swap(directory_descriptor, first, second):
                result = real_exchange(directory_descriptor, first, second)
                if (
                    first == ".provider-model-routing.journal"
                    or second == ".provider-model-routing.journal"
                ):
                    journal.write_bytes(external)
                    swapped["done"] = True
                return result

            with patch.object(
                provider_config,
                "_exchange_paths_at",
                side_effect=exchange_then_swap,
            ):
                with self.assertRaises(ValidationError):
                    provider_config.apply_model_routing_update(
                        codex_home,
                        "recovered-full",
                        "recovered-light",
                    )

            self.assertTrue(swapped["done"])
            self.assertEqual(journal.read_bytes(), external)

    def test_models_only_recovers_when_killed_during_journal_rewrite(self):
        """Killing a journal rewrite must leave the prior complete recovery record."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            child_code = """
import os
import signal
from pathlib import Path
import scripts.provider_config as provider_config

home = Path(os.environ["TEST_CODEX_HOME"])
real_replace = provider_config._atomic_replace_content_at
real_write_all = provider_config._write_all
armed = {"value": False}

def replace_then_arm(directory_descriptor, state, content):
    result = real_replace(directory_descriptor, state, content)
    armed["value"] = True
    return result

def terminate_during_next_write(descriptor, content):
    if armed["value"]:
        real_write_all(descriptor, content[:max(1, len(content) // 2)])
        os.kill(os.getpid(), signal.SIGKILL)
    return real_write_all(descriptor, content)

provider_config._atomic_replace_content_at = replace_then_arm
provider_config._write_all = terminate_during_next_write
provider_config.apply_model_routing_update(home, "recovered-full", "recovered-light")
"""
            child = subprocess.run(
                [sys.executable, "-c", child_code],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=dict(os.environ, TEST_CODEX_HOME=str(codex_home)),
            )

            self.assertEqual(child.returncode, -signal.SIGKILL)
            lock = codex_home / ".provider-model-routing.lock"
            journal_path = codex_home / ".provider-model-routing.journal"
            self.assertTrue(lock.exists())
            self.assertEqual(lock.read_bytes(), b"")
            envelope = json.loads(journal_path.read_text(encoding="utf-8"))
            self.assertEqual(envelope["journal_version"], 1)
            self.assertEqual(envelope["payload"]["phase"], "applying")
            self.assertEqual(len(envelope["sha256"]), 64)

            provider_config.apply_model_routing_update(
                codex_home,
                "recovered-full",
                "recovered-light",
            )

            self.assertTrue(lock.exists())
            self.assertEqual(lock.read_bytes(), b"")
            self.assertFalse(journal_path.exists())
            self.assertFalse(
                list(codex_home.glob(".provider-model-routing.journal.tmp.*"))
            )
            self.assertIn(
                'model = "recovered-full"',
                (codex_home / "config.toml").read_text(encoding="utf-8"),
            )

    def test_models_only_recovers_when_killed_after_journal_replace(self):
        """Killing before the journal directory sync must leave a complete new record."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            child_code = """
import os
import signal
from pathlib import Path
import scripts.provider_config as provider_config

home = Path(os.environ["TEST_CODEX_HOME"])
real_replace = provider_config._atomic_replace_content_at
real_fsync_directory = provider_config._fsync_directory
armed = {"value": False}

def replace_then_arm(directory_descriptor, state, content):
    result = real_replace(directory_descriptor, state, content)
    armed["value"] = True
    return result

def terminate_before_next_directory_sync(directory_descriptor):
    if armed["value"]:
        os.kill(os.getpid(), signal.SIGKILL)
    return real_fsync_directory(directory_descriptor)

provider_config._atomic_replace_content_at = replace_then_arm
provider_config._fsync_directory = terminate_before_next_directory_sync
provider_config.apply_model_routing_update(home, "recovered-full", "recovered-light")
"""
            child = subprocess.run(
                [sys.executable, "-c", child_code],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=dict(os.environ, TEST_CODEX_HOME=str(codex_home)),
            )

            self.assertEqual(child.returncode, -signal.SIGKILL)
            journal_path = codex_home / ".provider-model-routing.journal"
            envelope = json.loads(journal_path.read_text(encoding="utf-8"))
            self.assertEqual(envelope["payload"]["phase"], "applying")
            canonical = json.dumps(
                envelope["payload"],
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            self.assertEqual(
                envelope["sha256"],
                hashlib.sha256(canonical).hexdigest(),
            )

            provider_config.apply_model_routing_update(
                codex_home,
                "recovered-full",
                "recovered-light",
            )

            self.assertFalse(journal_path.exists())
            self.assertIn(
                'model = "recovered-light"',
                (codex_home / "agents" / "review-spec.toml").read_text(
                    encoding="utf-8"
                ),
            )

    def test_models_only_recovers_a_hard_terminated_partial_transaction(self):
        """A dead owner must be recovered without deleting a blind empty lock."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            child_code = """
import os
import signal
from pathlib import Path
import scripts.provider_config as provider_config

home = Path(os.environ["TEST_CODEX_HOME"])
real_replace = provider_config._atomic_replace_content_at
replacements = {"count": 0}

def replace_then_terminate(directory_descriptor, state, content):
    result = real_replace(directory_descriptor, state, content)
    replacements["count"] += 1
    if replacements["count"] == 1:
        os.kill(os.getpid(), signal.SIGKILL)
    return result

provider_config._atomic_replace_content_at = replace_then_terminate
provider_config.apply_model_routing_update(home, "recovered-full", "recovered-light")
"""
            child = subprocess.run(
                [sys.executable, "-c", child_code],
                check=False,
                capture_output=True,
                text=True,
                cwd=ROOT,
                env=dict(os.environ, TEST_CODEX_HOME=str(codex_home)),
            )

            self.assertEqual(child.returncode, -signal.SIGKILL)
            lock = codex_home / ".provider-model-routing.lock"
            journal_path = codex_home / ".provider-model-routing.journal"
            self.assertTrue(lock.exists())
            self.assertEqual(lock.read_bytes(), b"")
            envelope = json.loads(journal_path.read_text(encoding="utf-8"))
            self.assertEqual(envelope["journal_version"], 1)
            self.assertEqual(len(envelope["sha256"]), 64)
            journal = envelope["payload"]
            self.assertEqual(journal["version"], 1)
            self.assertEqual(journal["phase"], "applying")
            self.assertIsInstance(journal["owner"]["pid"], int)
            self.assertGreater(journal["owner"]["pid"], 0)
            self.assertNotEqual(journal["owner"]["pid"], os.getpid())
            self.assertTrue(journal["transaction_id"])
            self.assertTrue(all(target["backup"] for target in journal["targets"]))
            self.assertTrue(all(target["desired_sha256"] for target in journal["targets"]))

            provider_config.apply_model_routing_update(
                codex_home,
                "recovered-full",
                "recovered-light",
            )

            self.assertTrue(lock.exists())
            self.assertEqual(lock.read_bytes(), b"")
            self.assertFalse(journal_path.exists())
            self.assertIn(
                'model = "recovered-full"',
                (codex_home / "config.toml").read_text(encoding="utf-8"),
            )
            self.assertIn(
                'model = "recovered-light"',
                (codex_home / "agents" / "review-spec.toml").read_text(
                    encoding="utf-8"
                ),
            )

    def test_models_only_skips_a_broken_symlink_backup_collision(self):
        """Following or reusing a broken backup symlink can escape or block the target directory."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            codex_home = self.create_managed_codex_home(temporary)
            broken_backup = codex_home / "config.toml.backup.1"
            outside_target = temporary / "missing-backup-target"
            broken_backup.symlink_to(outside_target)

            backups = provider_config.apply_model_routing_update(
                codex_home,
                "gpt-5.6-sol",
                "gpt-5.6-luna",
            )

            self.assertTrue(broken_backup.is_symlink())
            self.assertFalse(outside_target.exists())
            self.assertIn("config.toml.backup.2", {backup.name for backup in backups.values()})
            self.assertTrue((codex_home / "config.toml.backup.2").is_file())

    def test_models_only_refuses_an_agent_directory_symlink_outside_codex_home(self):
        """An owned-looking file under an escaped parent must not authorize outside writes."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            codex_home = self.create_managed_codex_home(temporary)
            agents = codex_home / "agents"
            outside_agents = temporary / "outside-agents"
            agents.rename(outside_agents)
            agents.symlink_to(outside_agents, target_is_directory=True)
            outside_before = self.tree_contents(outside_agents)

            with self.assertRaises(ValidationError):
                provider_config.plan_model_routing_update(
                    codex_home,
                    "gpt-5.6-sol",
                    "gpt-5.6-luna",
                )

            self.assertEqual(self.tree_contents(outside_agents), outside_before)
            self.assertFalse(list(outside_agents.rglob("*.backup.*")))

    def test_models_only_requires_tomllib_before_rewriting_unrelated_malformed_syntax(self):
        """Without a full parser, malformed unrelated TOML must not be rewritten."""
        with tempfile.TemporaryDirectory() as directory:
            codex_home = self.create_managed_codex_home(Path(directory))
            config = codex_home / "config.toml"
            config.write_text(
                config.read_text(encoding="utf-8") + "broken =\n",
                encoding="utf-8",
            )
            before = self.tree_contents(codex_home)
            real_import = builtins.__import__

            def import_without_tomllib(name, *args, **kwargs):
                if name == "tomllib":
                    raise ImportError("simulated missing tomllib")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=import_without_tomllib):
                with self.assertRaisesRegex(ValidationError, "Python 3.11"):
                    provider_config.apply_model_routing_update(
                        codex_home,
                        "gpt-5.6-sol",
                        "gpt-5.6-luna",
                    )

            self.assertEqual(self.tree_contents(codex_home), before)
            self.assertFalse(list(codex_home.rglob("*.backup.*")))

    def test_models_only_rolls_back_when_parent_identity_changes_after_planning(self):
        """A post-validation directory swap must not redirect replacements outside the home."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            codex_home = self.create_managed_codex_home(temporary)
            config_before = (codex_home / "config.toml").read_bytes()
            guidance_before = (codex_home / "AGENTS.md").read_bytes()
            agents = codex_home / "agents"
            outside_agents = temporary / "outside-agents"
            outside_before = self.tree_contents(agents)
            real_replace_content = provider_config._atomic_replace_content_at
            replacements = {"count": 0}

            def replace_then_swap(directory_descriptor, state, content):
                result = real_replace_content(directory_descriptor, state, content)
                replacements["count"] += 1
                if replacements["count"] == 1:
                    agents.rename(outside_agents)
                    agents.symlink_to(outside_agents, target_is_directory=True)
                return result

            with patch.object(
                provider_config,
                "_atomic_replace_content_at",
                side_effect=replace_then_swap,
            ):
                with self.assertRaisesRegex(ValidationError, "changed"):
                    provider_config.apply_model_routing_update(
                        codex_home,
                        "gpt-5.6-sol",
                        "gpt-5.6-luna",
                    )

            self.assertEqual((codex_home / "config.toml").read_bytes(), config_before)
            self.assertEqual((codex_home / "AGENTS.md").read_bytes(), guidance_before)
            outside_after = self.tree_contents(outside_agents)
            for relative, contents in outside_before.items():
                self.assertEqual(outside_after[relative], contents, relative)

    def test_models_only_never_follows_parent_swap_after_final_validation(self):
        """Mutation must use stable directories even if the pathname changes after checking."""
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            codex_home = self.create_managed_codex_home(temporary)
            agents = codex_home / "agents"
            validated_agents_path = agents.resolve()
            moved_agents = temporary / "moved-validated-agents"
            attack_target = temporary / "attack-target"
            original_agents = self.tree_contents(agents)
            attack_target.mkdir()
            for relative, contents in original_agents.items():
                destination = attack_target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(contents)
            attack_before = self.tree_contents(attack_target)
            real_assert = provider_config._assert_managed_file_unchanged
            swapped = {"done": False}
            agent_validations = {"count": 0}

            def validate_then_swap(state):
                result = real_assert(state)
                if state.path.parent == validated_agents_path:
                    agent_validations["count"] += 1
                if (
                    agent_validations["count"] == len(self.managed_agent_models) + 1
                    and not swapped["done"]
                ):
                    agents.rename(moved_agents)
                    agents.symlink_to(attack_target, target_is_directory=True)
                    swapped["done"] = True
                return result

            with patch.object(
                provider_config,
                "_assert_managed_file_unchanged",
                side_effect=validate_then_swap,
            ):
                with self.assertRaises((ValidationError, OSError)):
                    provider_config.apply_model_routing_update(
                        codex_home,
                        "gpt-5.6-sol",
                        "gpt-5.6-luna",
                    )

            self.assertTrue(swapped["done"])
            self.assertEqual(self.tree_contents(attack_target), attack_before)
            moved_after = self.tree_contents(moved_agents)
            for relative, contents in original_agents.items():
                self.assertEqual(moved_after[relative], contents, relative)


if __name__ == "__main__":
    unittest.main()
