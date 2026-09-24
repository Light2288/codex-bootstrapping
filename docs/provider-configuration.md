# Provider configuration

`scripts/configure-provider.zsh` optionally configures a custom Codex model
provider in the user-level `config.toml`. It is independent of the workflow
bootstrap; run it only when a provider administrator has supplied a compatible
Responses API endpoint and credential.

```zsh
zsh scripts/configure-provider.zsh
```

With no focused-mode option, this remains the complete flow: provider ID,
endpoint, transport, authentication mode, credential, and default model are
reviewed together.

The wizard asks for every provider setting and accepts these reviewed IBM ICA
values when Enter is pressed:

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
| Credential storage | `keychain` |

The wire API is intentionally limited to `responses`. Enable WebSockets only
when the provider confirms support for the Responses WebSocket transport.

Before it writes anything, the wizard prints a redacted preview and asks for
confirmation. It then makes a timestamped backup of an existing `config.toml`
and atomically replaces it. On Python 3.11 or newer, the resulting TOML is
parsed with `tomllib` before it is written.

## Credential storage

The default `keychain` mode stores the token with the bundled macOS
Security.framework helper, then lets Codex retrieve it through command-backed
provider authentication. The key is entered with hidden terminal input only
after confirmation and is sent to the helper over standard input. It is not
written to TOML, the preview, command arguments, or the wizard's output. If
Security.framework cannot be loaded, the wizard stops before changing either
the Keychain or `config.toml`.

`environment` mode instead writes the provider's `env_key` name into TOML; it
does not write a token or modify shell startup files. Make the named environment
variable available to the Codex process yourself. GUI applications do not
normally inherit variables exported by shell profiles.

The two modes are exclusive: a provider uses either the Keychain-backed `auth`
table or an `env_key`, never both.

## Focused reconfiguration

Rotate only the Keychain credential for a provider with:

```zsh
zsh scripts/configure-provider.zsh --credential-only
```

This prompts for the provider ID, confirmation, and a hidden credential. It
uses the same standard-input-to-Keychain helper as the complete flow. The
transformer validates the provider ID, but credential-only mode skips its
configuration merge/write path and does not change any configuration file.

Update only managed model routing with:

```zsh
zsh scripts/configure-provider.zsh --models-only
```

Models-only mode selects Python 3.11 or newer so every TOML target is fully
parsed before any backup or write; it exits without changes if no suitable
interpreter is available.

The full and light prompts default to `gpt-5.6-sol` and `gpt-5.6-luna`.
After preview and confirmation, the transaction updates the top-level `model`
in `config.toml`, the `full` and `light` values inside the marked
`personal-workflows` block in `AGENTS.md`, and these owned agent assignments:

| Model role | Managed agents |
| --- | --- |
| Light | `review-spec` |
| Full | `review-quality`, `review-audit`, `doc-analyst`, `document-worker` |

Every target must already exist and carry its expected ownership marker or
identity. Missing, malformed, symlinked, or unmanaged targets abort before any
write. `--config` identifies the exact configuration filename; models-only
mode never silently substitutes a sibling `config.toml`. Changed files receive
collision-safe sibling backups and are replaced with atomic pathname exchange.
The transaction records the owner, phase, targets, backups, desired hashes,
and post-replacement identities in a checksummed
`.provider-model-routing.journal`. Journal rewrites use a synced sibling file,
atomic replacement, and a directory sync, so termination leaves either the
previous complete record or the next complete record. The persistent
`.provider-model-routing.lock` supplies one stable operating-system lock inode
and contains no journal data. If the owner is terminated, the next run takes
the released lock, verifies the journal and backups, restores the
pre-transaction bytes, and only then starts a fresh update. Nonempty legacy
lock journals are migrated before recovery. An unexpected external target
swap or edit, or an invalid journal checksum, stops recovery safely instead of
overwriting data. If legacy and atomic journals coexist, they must describe the
same transaction before legacy bytes are cleared. Final cleanup atomically
exchanges and verifies the expected journal, preserving swapped or corrupted
evidence instead of unlinking it; do not delete the journal to bypass that
refusal. Unrelated
configuration, guidance, agents, and plugin caches are outside this mode's
write set. Supported full/light overrides remain valid through profile checks
and bootstrap reinstalls. The two focused modes cannot be combined, and
provider or endpoint changes remain exclusive to the complete flow.

## Safe inspection

Use either inspection mode before changing a real Codex home:

```zsh
zsh scripts/configure-provider.zsh --check
zsh scripts/configure-provider.zsh --dry-run
```

Both modes avoid credential prompts, Keychain writes, configuration writes, and
directory creation. Pass `--config /path/to/config.toml` to inspect a different
target. Add `--smoke-test` during a confirmed normal run to invoke the
read-only `codex --version` smoke check after configuration. Focused modes
reject `--smoke-test` before prompting or mutation because they do not run the
complete post-configuration flow.

The lower-level transformer has no API-key option. It can validate or apply
non-secret settings directly when automation needs it:

```zsh
python3 scripts/provider_config.py --config /path/to/config.toml --dry-run
```
