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

The plugin is provider-neutral. It does not include Figma configuration,
credentials, local Codex state, or a vendored copy of Superpowers.

## Use the distribution

Clone this repository, then register its root and install the plugin:

```sh
codex plugin marketplace add /path/to/codex-bootstrapping
codex plugin add personal-workflows@personal
```

Install Superpowers as a runtime dependency through its configured marketplace.

To inspect profile changes without writing a Codex home, run:

```sh
python3 plugins/personal-workflows/scripts/install_profile.py \
  --codex-home /path/to/codex-home --check
```

The profile installer is explicit: use `--install` only after reviewing the
check-mode report. It preserves unrelated guidance and refuses to overwrite
an unmanaged agent file.

See [the workflow guide](docs/workflows.md) for the included skills. Future
bootstrap automation and provider configuration are documented as they are
added to this repository.

## Development

Run the distribution checks with:

```sh
python3 -m unittest discover -s tests -v
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change and
[SECURITY.md](SECURITY.md) for vulnerability reporting.

## License

This project is licensed under the [MIT License](LICENSE).
