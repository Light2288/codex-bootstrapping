# Troubleshooting

## Codex cannot be found

The bootstrap searches `CODEX_BOOTSTRAP_CODEX_CMD`, `PATH`, and the bundled
ChatGPT application binary. Install Codex from
<https://developers.openai.com/codex/> and rerun the check command. Check and
dry-run modes never download or install Codex.

## A `personal` marketplace conflicts

The bootstrap refuses to overwrite a marketplace with that name that points to
another location. Inspect it with `codex plugin marketplace list --json`, then
remove or rename the old marketplace through the Codex CLI only if it is no
longer needed. Re-run the bootstrap after resolving the conflict.

## Python 3.11 or newer is required for verification

macOS can provide an older Python as `python3`. Install Python 3.11+ and put
it on `PATH` as `python3.11`, `python3.12`, `python3.13`, or `python3`; then
rerun `zsh scripts/verify.zsh`. The installation and uninstall helpers remain
compatible with the system Python 3.7 where practical.

## The profile uninstall refuses an agent

Do not delete the file through this helper when it reports an unmanaged agent.
The filename is reserved by the profile but the content is not marked as owned
by `personal-workflows`; save, rename, or review the file yourself before
retrying. This guard prevents data loss.

## Provider setup is not part of bootstrap

The bootstrap deliberately does not configure a provider or credential. Use
the separate [provider configuration guide](provider-configuration.md) only
after your provider administrator has supplied compatible settings.
