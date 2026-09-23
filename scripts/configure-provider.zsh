#!/bin/zsh
# Interactive, secret-safe front end for scripts/provider_config.py.

emulate -LR zsh
setopt errexit nounset pipefail

script_dir=${0:A:h}
transformer="$script_dir/provider_config.py"
keychain_helper="$script_dir/keychain_helper.py"
keychain_helper_override="${CODEX_PROVIDER_KEYCHAIN_HELPER:-}"
config_path="${CODEX_HOME:-$HOME/.codex}/config.toml"
mode="apply"
smoke_test=false

usage() {
  print "Usage: ${0:t} [--config PATH] [--check | --dry-run] [--smoke-test]"
}

while (( $# > 0 )); do
  case "$1" in
    --config)
      (( $# >= 2 )) || { print -u2 "--config requires a path"; exit 2; }
      config_path="$2"
      shift 2
      ;;
    --check)
      [[ "$mode" == "apply" ]] || { print -u2 "--check and --dry-run cannot be combined"; exit 2; }
      mode="check"
      shift
      ;;
    --dry-run)
      [[ "$mode" == "apply" ]] || { print -u2 "--check and --dry-run cannot be combined"; exit 2; }
      mode="dry-run"
      shift
      ;;
    --smoke-test)
      smoke_test=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      print -u2 "unknown option: $1"
      usage >&2
      exit 2
      ;;
  esac
done

[[ -f "$transformer" ]] || { print -u2 "missing provider transformer: $transformer"; exit 1; }

provider_id="ibm_ica"
display_name="IBM ICA"
base_url="https://api.servicesessentials.ibm.com/v1"
model="gpt-5.6-sol"
reasoning_effort="high"
wire_api="responses"
credential_env_var="IBM_ICA_CODEX_API_KEY"
supports_websockets="false"
auth_mode="keychain"

transformer_args=(
  --config "$config_path"
  --provider-id "$provider_id"
  --display-name "$display_name"
  --base-url "$base_url"
  --model "$model"
  --reasoning-effort "$reasoning_effort"
  --wire-api "$wire_api"
  --credential-env-var "$credential_env_var"
  --supports-websockets "$supports_websockets"
  --auth-mode "$auth_mode"
)

if [[ "$mode" == "check" || "$mode" == "dry-run" ]]; then
  # Inspection modes intentionally do not request, store, or print a credential.
  exec python3 "$transformer" "${transformer_args[@]}" "--$mode"
fi

prompt_default() {
  local label="$1"
  local default_value="$2"
  local response=""
  printf '%s [%s]: ' "$label" "$default_value"
  IFS= read -r response
  REPLY="${response:-$default_value}"
}

run_keychain_helper() {
  if [[ -n "$keychain_helper_override" ]]; then
    "$keychain_helper_override" "$@"
  else
    python3 "$keychain_helper" "$@"
  fi
}

prompt_default "Provider ID" "$provider_id"; provider_id="$REPLY"
prompt_default "Display name" "$display_name"; display_name="$REPLY"
prompt_default "API base URL" "$base_url"; base_url="$REPLY"
prompt_default "Model" "$model"; model="$REPLY"
prompt_default "Reasoning effort" "$reasoning_effort"; reasoning_effort="$REPLY"
prompt_default "Wire API (responses only)" "$wire_api"; wire_api="$REPLY"
prompt_default "Credential environment variable" "$credential_env_var"; credential_env_var="$REPLY"
prompt_default "Responses WebSocket support (true/false)" "$supports_websockets"; supports_websockets="$REPLY"
prompt_default "Credential storage (keychain/environment)" "$auth_mode"; auth_mode="$REPLY"

transformer_args=(
  --config "$config_path"
  --provider-id "$provider_id"
  --display-name "$display_name"
  --base-url "$base_url"
  --model "$model"
  --reasoning-effort "$reasoning_effort"
  --wire-api "$wire_api"
  --credential-env-var "$credential_env_var"
  --supports-websockets "$supports_websockets"
  --auth-mode "$auth_mode"
)

print ""
python3 "$transformer" "${transformer_args[@]}" --dry-run
print ""
print "The preview is redacted: no API key is written to TOML or printed."
if [[ "$auth_mode" == "environment" ]]; then
  print "Environment mode does not write shell profiles; make $credential_env_var available to Codex yourself."
fi
printf 'Apply this configuration? [y/N]: '
IFS= read -r confirmation
[[ "$confirmation" == "y" || "$confirmation" == "Y" ]] || { print "No changes made."; exit 0; }

if [[ "$auth_mode" == "keychain" ]]; then
  service="codex-provider-$provider_id"
  if ! run_keychain_helper check --service "$service" --account "codex"; then
    print -u2 "Keychain helper is unavailable; no files were changed"
    exit 1
  fi
  print -n "API key (stored only in macOS Keychain; input hidden): "
  IFS= read -r -s api_key
  print ""
  [[ -n "$api_key" ]] || { print -u2 "API key cannot be empty"; exit 1; }
  prior_credential=""
  had_prior_credential=false
  if prior_credential=$(run_keychain_helper get --service "$service" --account "codex"); then
    had_prior_credential=true
  else
    lookup_status=$?
    if (( lookup_status != 44 )); then
      print -u2 "Could not inspect the existing macOS Keychain credential"
      exit 1
    fi
  fi
  if ! print -rn -- "$api_key" | run_keychain_helper set --service "$service" --account "codex"; then
    unset api_key
    print -u2 "Could not store the API key in macOS Keychain"
    exit 1
  fi
  unset api_key
fi

config_status=0
python3 "$transformer" "${transformer_args[@]}" || config_status=$?
if (( config_status != 0 )); then
  if [[ "$auth_mode" == "keychain" ]]; then
    if [[ "$had_prior_credential" == true ]]; then
      print -rn -- "$prior_credential" | run_keychain_helper set --service "$service" --account "codex" || {
        print -u2 "Configuration failed and the prior Keychain credential could not be restored"
        exit "$config_status"
      }
    else
      run_keychain_helper delete --service "$service" --account "codex" || {
        print -u2 "Configuration failed and the new Keychain credential could not be removed"
        exit "$config_status"
      }
    fi
  fi
  print -u2 "Provider configuration failed; Keychain state was rolled back"
  exit "$config_status"
fi

if [[ "$smoke_test" == true ]]; then
  if (( $+commands[codex] )); then
    codex --version
  else
    print -u2 "Codex smoke test skipped: codex was not found on PATH"
  fi
fi
