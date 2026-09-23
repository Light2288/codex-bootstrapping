# Provider configuration

`scripts/configure-provider.zsh` optionally configures a custom Codex model
provider in the user-level `config.toml`. It is independent of the workflow
bootstrap; run it only when a provider administrator has supplied a compatible
Responses API endpoint and credential.

```zsh
zsh scripts/configure-provider.zsh
```

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

The default `keychain` mode reads the token from a macOS Keychain item through
Codex's command-backed provider authentication. The key is entered with hidden
terminal input only after confirmation. It is not written to TOML, the preview,
or the wizard's output.

`environment` mode instead writes the provider's `env_key` name into TOML; it
does not write a token or modify shell startup files. Make the named environment
variable available to the Codex process yourself. GUI applications do not
normally inherit variables exported by shell profiles.

The two modes are exclusive: a provider uses either the Keychain-backed `auth`
table or an `env_key`, never both.

## Safe inspection

Use either inspection mode before changing a real Codex home:

```zsh
zsh scripts/configure-provider.zsh --check
zsh scripts/configure-provider.zsh --dry-run
```

Both modes avoid credential prompts, Keychain writes, configuration writes, and
directory creation. Pass `--config /path/to/config.toml` to inspect a different
target. Add `--smoke-test` during a confirmed normal run to invoke the
read-only `codex --version` smoke check after configuration.

The lower-level transformer has no API-key option. It can validate or apply
non-secret settings directly when automation needs it:

```zsh
python3 scripts/provider_config.py --config /path/to/config.toml --dry-run
```
