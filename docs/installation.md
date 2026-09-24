# Installation and lifecycle

## Bootstrap

On macOS, clone this repository and run the read-only checks before changing a
Codex home:

```sh
zsh scripts/bootstrap-macos.zsh --check
zsh scripts/bootstrap-macos.zsh --dry-run
```

Use `zsh scripts/bootstrap-macos.zsh` only after reviewing those reports. The
script may inspect the registered marketplaces before confirmation so it can
refuse a naming conflict, but it asks before every mutating Codex plugin
command and before the profile installer's explicit `--install` mode. It
locates `codex` from `CODEX_BOOTSTRAP_CODEX_CMD`, `PATH`, or the ChatGPT
application's bundled binary. If none is available, it links to the official
Codex installation page and does not install anything in check or dry-run
mode.

The normal bootstrap installs or verifies Superpowers, registers this checkout
as the `personal` marketplace, installs `personal-workflows@personal`, then
runs the copied profile installer with `--install` and `--check`. It never
invokes provider configuration. A pre-existing `personal` marketplace pointing
to another path is a conflict that must be resolved manually.

`--check` is a strict target-home health check: it verifies semantic plugin
manifests in the target cache, the exact managed guidance block, and each
managed agent's contents without starting Codex. It exits nonzero when any
required artifact is missing, malformed, or drifted. `--dry-run` remains a
non-writing plan and may describe missing components without failing.

## Updating

Pull the desired revision and rerun the bootstrap. The marketplace entry,
managed guidance block, and managed agents are idempotent. Existing managed
files may receive collision-safe backups from the profile installer; unrelated
agent files are never replaced.

To rotate a configured provider credential without changing `config.toml`, use
`zsh scripts/configure-provider.zsh --credential-only`. To update the managed
full/light routing after the profile is installed, use
`zsh scripts/configure-provider.zsh --models-only`. The latter validates all
owned targets before writing, creates sibling backups, applies atomic
pathname exchanges, and rolls already-written files back if the transaction
fails. A persistent lock file coordinates writers, while a separate
atomically replaced checksummed journal lets a later run recover a process
terminated during either a target update or a journal update. It refuses
missing, malformed, symlinked, unmanaged, corrupt-journal, or externally
changed targets instead of overwriting them. Supported custom assignments are
normalized through later profile checks and bootstrap reinstalls. See
[provider configuration](provider-configuration.md) for the prompts and exact
assignment rules.

## Verification

Run `zsh scripts/verify.zsh` from the repository root. Verification requires
Python 3.11+ because the copied plugin's validation uses `tomllib`. The
verifier discovers a suitable interpreter instead of relying on macOS's older
default Python, and it does not read or write `~/.codex` or `~/.agents`.

## Removal

First inspect the removal plan:

```sh
python3 scripts/uninstall-profile.py --check
```

Then remove only the profile artifacts installed by this plugin:

```sh
python3 scripts/uninstall-profile.py --uninstall
```

This leaves unrelated guidance and agents in place and refuses to delete an
unmanaged agent sharing a managed filename. To remove the plugin or repository
marketplace itself, use the Codex plugin CLI after reviewing its current help:

```sh
codex plugin remove personal-workflows@personal
codex plugin marketplace remove personal
```

Those CLI actions are intentionally not performed by the profile uninstall
helper.

## Release smoke test

Before publishing a release, validate the confirmed missing-Codex download
path on a clean macOS account. Automated tests deliberately use temporary
homes and fake Codex executables, so they do not download or execute the
network installer.
