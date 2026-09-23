# Installation and lifecycle

## Bootstrap

On macOS, clone this repository and run the read-only checks before changing a
Codex home:

```sh
zsh scripts/bootstrap-macos.zsh --check
zsh scripts/bootstrap-macos.zsh --dry-run
```

Use `zsh scripts/bootstrap-macos.zsh` only after reviewing those reports. The
script asks for confirmation before it invokes any Codex plugin command or the
profile installer's explicit `--install` mode. It locates `codex` from
`CODEX_BOOTSTRAP_CODEX_CMD`, `PATH`, or the ChatGPT application's bundled
binary. If none is available, it links to the official Codex installation page
and does not install anything in check or dry-run mode.

The normal bootstrap installs or verifies Superpowers, registers this checkout
as the `personal` marketplace, installs `personal-workflows@personal`, then
runs the copied profile installer with `--install` and `--check`. It never
invokes provider configuration. A pre-existing `personal` marketplace pointing
to another path is a conflict that must be resolved manually.

## Updating

Pull the desired revision and rerun the bootstrap. The marketplace entry,
managed guidance block, and managed agents are idempotent. Existing managed
files may receive collision-safe backups from the profile installer; unrelated
agent files are never replaced.

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
