# Codex Bootstrapping

Codex Bootstrapping is a public, macOS-oriented distribution of the
`personal-workflows` plugin for Codex. It packages spec-driven engineering,
architecture, document, and repository-audit workflows that extend
Superpowers.

## What is included

- The `personal` Codex marketplace and `personal-workflows` plugin.
- Thirteen workflow skills and five managed, read-only Codex agent profiles.
- A profile installer that adds only the plugin's marked guidance and managed
  agents to a chosen Codex home.
- Public project, security, contribution, and workflow documentation.
- A macOS bootstrap, repository verifier, and safe profile-uninstall helper.

The plugin is provider-neutral. It does not include credentials, local Codex
state, or a vendored copy of Superpowers.

## Install on macOS

Clone the repository and review the bootstrap's planned changes first:

```sh
zsh scripts/bootstrap-macos.zsh --check
zsh scripts/bootstrap-macos.zsh --dry-run
```

Run the confirmed installation only when the report is correct:

```sh
zsh scripts/bootstrap-macos.zsh
```

The bootstrap is macOS-only. It finds Codex on `PATH`, through
`CODEX_BOOTSTRAP_CODEX_CMD`, or in the ChatGPT bundle. If Codex is absent it
prints the official installation page and asks before any installation action.
It installs or verifies the Superpowers runtime dependency, registers this
repository's `personal` marketplace, installs `personal-workflows`, and then
explicitly runs the profile install and check commands. It never configures a
model provider. A marketplace named `personal` that points elsewhere is a hard
error, not an overwrite.

After a successful installation, start a new Codex task so the global routing
guidance is loaded. The optional provider wizard is separate; see
[provider configuration](docs/provider-configuration.md) only if you need a
compatible custom provider.

## Update, verify, and uninstall

Re-run the bootstrap after pulling updates. It is idempotent: it does not add
duplicate marketplace registrations, agent files, or guidance blocks.

Run the repository's no-user-state verifier with:

```sh
zsh scripts/verify.zsh
```

The verifier requires Python 3.11 or newer for `tomllib`; it prints an
actionable requirement if no suitable interpreter is available. It runs the
Python suites, shell syntax checks, plugin contract checks, manifest checks,
secret scanning, and marketplace/manifest safety checks without reading or
changing your Codex home.

To inspect or remove only this plugin's global profile artifacts:

```sh
python3 scripts/uninstall-profile.py --check
python3 scripts/uninstall-profile.py --uninstall
```

The uninstall helper removes only the marked `personal-workflows` guidance
block and agent files carrying the plugin's managed header. It refuses a
same-named unmanaged agent. Plugin and marketplace removal are deliberate
Codex CLI actions, documented in [installation](docs/installation.md).

To inspect profile changes without writing a Codex home, run:

```sh
python3 plugins/personal-workflows/scripts/install_profile.py \
  --codex-home /path/to/codex-home --check
```

The profile installer is explicit: use `--install` only after reviewing the
check-mode report. It preserves unrelated guidance and refuses to overwrite
an unmanaged agent file.

See [the workflow guide](docs/workflows.md) for the included skills and
[troubleshooting](docs/troubleshooting.md) for recovery steps.

## Development

Run the distribution checks with:

```sh
python3 -m unittest discover -s tests -v
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change and
[SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

This project is licensed under the [MIT License](LICENSE).
