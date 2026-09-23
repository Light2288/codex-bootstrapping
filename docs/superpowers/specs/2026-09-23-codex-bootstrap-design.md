# Codex Bootstrapping Design

## Goal

Provide a public, reproducible macOS repository that installs the existing
`personal-workflows` Codex plugin and its global agent profile without
modifying the source installation used to build this repository. Provide a
separate, optional provider configurator based on the reviewed IBM ICA
installer, with every provider-specific value confirmed interactively.

## Scope

The repository contains:

- A copy of the verified `personal-workflows` marketplace and plugin source.
- A provider-neutral macOS bootstrap script for Codex, Superpowers, the
  repository marketplace, `personal-workflows`, its global agents, and its
  global routing guidance.
- A separate interactive provider configuration script.
- Verification, rollback/uninstall support, tests, and public documentation.

The repository does not contain or configure Figma. It does not vendor
Superpowers, Codex caches, user credentials, shell configuration, Codex
configuration, generated backups, or other machine-local state.

## Source Preservation

The current plugin source at `/Users/davide/.agents/plugins/personal` is a
read-only migration source. Repository creation copies tracked plugin and
marketplace files from it. Nothing in this project may edit the source tree,
`~/.codex`, or `~/.agents` during repository construction or tests.

When an end user explicitly runs an installer, the installer may update the
user's Codex configuration after preview and confirmation. All managed file
changes must be idempotent, atomic where practical, and backed up before an
existing file is replaced.

## Repository Layout

```text
.agents/plugins/marketplace.json
plugins/personal-workflows/...
scripts/bootstrap-macos.zsh
scripts/configure-provider.zsh
scripts/provider_config.py
scripts/verify.zsh
scripts/uninstall-profile.py
tests/...
docs/installation.md
docs/provider-configuration.md
docs/workflows.md
docs/troubleshooting.md
README.md
LICENSE
SECURITY.md
CHANGELOG.md
CONTRIBUTING.md
```

## Provider-Neutral Bootstrap

`scripts/bootstrap-macos.zsh` runs only on macOS and must:

1. Locate `codex` from `PATH`, `CODEX_BOOTSTRAP_CODEX_CMD`, or the bundled
   executable at `/Applications/ChatGPT.app/Contents/Resources/codex`.
2. If Codex is missing, explain the official installation source and ask
   before downloading and running the official installer. Never install
   silently.
3. Confirm that Git, Python 3, and zsh are available.
4. Install or verify Superpowers from the configured curated marketplace.
5. Add this repository as a marketplace without duplicating an existing
   registration, then install `personal-workflows@personal`.
6. Run the plugin's `install_profile.py --install` and `--check` commands.
7. Run repository verification and remind the user to start a new Codex task.

The bootstrap supports `--check` and `--dry-run`. `--check` performs no
writes and reports missing or inconsistent components. `--dry-run` prints
the mutations it would request. Re-running a successful installation must
not create duplicate marketplace entries, guidance blocks, or agents.

## Interactive Provider Configuration

`scripts/configure-provider.zsh` is independent of the workflow bootstrap.
It prompts for every provider-specific setting, showing the reviewed IBM ICA
values as defaults:

| Setting | Default |
| --- | --- |
| Provider ID | `ibm_ica` |
| Display name | `IBM ICA` |
| API base URL | `https://api.servicesessentials.ibm.com/v1` |
| Model | `gpt-5.6-sol` |
| Reasoning effort | `high` |
| Wire API | `responses` |
| Credential environment variable | `IBM_ICA_CODEX_API_KEY` |
| Responses WebSocket support | `false` |

The wire API is displayed and confirmed but validated as `responses`, the
only value Codex currently supports. WebSockets default to disabled because
the flag declares provider compatibility with the Responses WebSocket
transport; it is enabled only when the user confirms their provider supports
it.

The API key is read with hidden input. The default storage mode is macOS
Keychain, configured through Codex command-backed provider authentication so
the secret is not written to TOML or a shell profile. An environment-variable
mode is available for compatibility, but the script explains that GUI apps
do not normally inherit shell startup files and does not write the secret to
a shell profile. In that mode the user is responsible for making the named
variable available to Codex.

Before any mutation, the script prints a redacted configuration preview and
asks for confirmation. It backs up an existing `config.toml`, writes
atomically, validates the resulting TOML when Python `tomllib` is available,
and optionally performs a read-only Codex smoke test. It supports `--check`
and `--dry-run`; neither mode stores credentials or writes configuration.

Provider configuration preserves unrelated TOML content while replacing the
three managed root keys (`model`, `model_reasoning_effort`, and
`model_provider`) and the selected provider table. Ambiguous or malformed
managed input fails without replacing the original file.

## Verification and Uninstall

Repository verification checks shell syntax, Python tests, plugin manifest
and marketplace structure, skill layout, profile consistency, and absence of
forbidden Figma configuration or likely secrets.

The uninstall helper removes only files and marked guidance managed by
`personal-workflows`. It refuses to remove unrelated or manually managed
agent files. Removing the installed plugin or marketplace remains an explicit
Codex CLI action documented for the user.

## Public Repository and Security

- No credential, `.env`, machine configuration, cache, or backup is tracked.
- The public plugin remains provider-neutral; IBM ICA is merely the default
  example in the optional configurator.
- Superpowers is a runtime dependency and is never vendored.
- Installer downloads use the official Codex URL and occur only after user
  confirmation.
- Secrets never appear in command output, dry-run output, previews, logs, or
  tests.
- The project uses an MIT license and documents responsible disclosure.

## Acceptance Criteria

- A clean macOS user can clone the repository and follow the README to install
  Codex, Superpowers, `personal-workflows`, five global agents, and routing
  guidance.
- The copied plugin contains all 13 approved skills and five approved agents.
- Bootstrap check and dry-run modes perform no writes.
- Provider configuration asks for all listed settings and accepts Enter for
  the documented defaults.
- No Figma reference is present in executable configuration paths.
- Provider secrets are redacted and never committed or written to TOML.
- Repeated installation is idempotent.
- Automated tests and validation pass without reading or changing live Codex
  state.

