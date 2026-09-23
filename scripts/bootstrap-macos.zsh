#!/bin/zsh
# Install or inspect the provider-neutral personal-workflows distribution.

emulate -LR zsh
setopt errexit nounset pipefail

script_dir=${0:A:h}
repository_root=${script_dir:h}
profile_installer="$repository_root/plugins/personal-workflows/scripts/install_profile.py"
codex_home="${CODEX_HOME:-$HOME/.codex}"
mode="install"
official_install_url="https://developers.openai.com/codex/"
official_installer_url="${CODEX_BOOTSTRAP_INSTALL_URL:-https://github.com/openai/codex/releases/latest/download/codex-installer.sh}"
bundled_codex="${CODEX_BOOTSTRAP_BUNDLED_CODEX:-/Applications/ChatGPT.app/Contents/Resources/codex}"

usage() {
  print "Usage: ${0:t} [--codex-home PATH] [--check | --dry-run]"
}

while (( $# > 0 )); do
  case "$1" in
    --codex-home)
      (( $# >= 2 )) || { print -u2 "--codex-home requires a path"; exit 2; }
      codex_home="$2"
      shift 2
      ;;
    --check|--dry-run)
      [[ "$mode" == "install" ]] || { print -u2 "--check and --dry-run cannot be combined"; exit 2; }
      mode="${1#--}"
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

resolve_codex() {
  local candidate=""
  if [[ -n "${CODEX_BOOTSTRAP_CODEX_CMD:-}" ]]; then
    candidate="${CODEX_BOOTSTRAP_CODEX_CMD}"
    if [[ -x "$candidate" ]]; then
      print -r -- "$candidate"
      return 0
    fi
    if (( $+commands[$candidate] )); then
      whence -p "$candidate"
      return 0
    fi
  fi
  if (( $+commands[codex] )); then
    whence -p codex
    return 0
  fi
  if [[ -x "$bundled_codex" ]]; then
    print -r -- "$bundled_codex"
    return 0
  fi
  return 1
}

require_dependencies() {
  local dependency
  for dependency in git python3 zsh; do
    if ! (( $+commands[$dependency] )); then
      print -u2 "missing required dependency: $dependency"
      return 1
    fi
  done
}

marketplace_state() {
  local marketplace_json="$1"
  MARKETPLACE_JSON="$marketplace_json" REPOSITORY_ROOT="$repository_root" python3 -c '
import json
import os
import sys

try:
    payload = json.loads(os.environ["MARKETPLACE_JSON"])
except (KeyError, ValueError) as error:
    print("could not parse Codex marketplace output: {0}".format(error), file=sys.stderr)
    raise SystemExit(2)
items = payload.get("marketplaces", []) if isinstance(payload, dict) else payload
if not isinstance(items, list):
    print("could not parse Codex marketplace output", file=sys.stderr)
    raise SystemExit(2)
root = os.path.realpath(os.environ["REPOSITORY_ROOT"])
for item in items:
    if not isinstance(item, dict) or item.get("name") != "personal":
        continue
    paths = [item.get("root"), item.get("path"), item.get("location")]
    for source in (item.get("source"), item.get("marketplaceSource")):
        if isinstance(source, str):
            paths.append(source)
        elif isinstance(source, dict):
            paths.extend((source.get("root"), source.get("path"), source.get("location")))
            if isinstance(source.get("source"), str):
                paths.append(source["source"])
    if any(path and os.path.realpath(path) == root for path in paths):
        print("registered")
        raise SystemExit(0)
    print("conflict")
    raise SystemExit(3)
print("missing")
'
}

plugin_cache_state() {
  local plugin_name="$1"
  local manifest contents
  for manifest in "$codex_home"/plugins/cache/**/.codex-plugin/plugin.json(N); do
    contents="$(<"$manifest")"
    if [[ "$contents" == *"\"name\": \"$plugin_name\""* ]]; then
      print "installed"
      return 0
    fi
  done
  print "missing"
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  print -u2 "bootstrap-macos.zsh supports macOS only"
  exit 1
fi
require_dependencies

codex_command=""
if ! codex_command=$(resolve_codex); then
  print -u2 "Codex was not found. Install it from $official_install_url"
  if [[ "$mode" != "install" ]]; then
    exit 1
  fi
  printf 'Download and run the official Codex installer from %s? [y/N]: ' "$official_install_url"
  IFS= read -r confirmation
  [[ "$confirmation" == "y" || "$confirmation" == "Y" ]] || { print "No changes made."; exit 1; }
  installer_path="$(mktemp -t codex-bootstrap-installer.XXXXXX)"
  trap 'rm -f -- "$installer_path"' EXIT
  curl -fsSL "$official_installer_url" -o "$installer_path"
  zsh "$installer_path"
  codex_command="$(resolve_codex)" || {
    print -u2 "Codex installation did not make a Codex command available. Rerun after completing the official installer."
    exit 1
  }
fi

print "Repository root: $repository_root"
print "Codex command: $codex_command"

if [[ "$mode" == "check" || "$mode" == "dry-run" ]]; then
  print "Marketplace: unknown (Codex is not invoked in $mode mode)."
  print "Superpowers: $(plugin_cache_state superpowers) in $codex_home"
  print "personal-workflows: $(plugin_cache_state personal-workflows) in $codex_home"
  if [[ "$mode" == "check" ]]; then
    print "Check mode: no changes will be made."
  else
    print "Dry run: would install or verify Superpowers, register this marketplace, install personal-workflows, and run the profile installer."
  fi
  exit 0
fi

marketplaces="$(CODEX_HOME="$codex_home" "$codex_command" plugin marketplace list --json)"
state="$(marketplace_state "$marketplaces")" || marketplace_status=$?
if [[ "${marketplace_status:-0}" -eq 3 || "$state" == "conflict" ]]; then
  print -u2 "conflicting marketplace named personal is already registered; refusing to overwrite it"
  exit 1
elif [[ "${marketplace_status:-0}" -ne 0 ]]; then
  exit "$marketplace_status"
fi

print "This will install or verify Superpowers and personal-workflows, then update $codex_home."
printf 'Continue? [y/N]: '
IFS= read -r confirmation
[[ "$confirmation" == "y" || "$confirmation" == "Y" ]] || { print "No changes made."; exit 0; }

CODEX_HOME="$codex_home" "$codex_command" plugin add superpowers@openai-curated-remote
if [[ "$state" == "missing" ]]; then
  CODEX_HOME="$codex_home" "$codex_command" plugin marketplace add "$repository_root"
fi
CODEX_HOME="$codex_home" "$codex_command" plugin add personal-workflows@personal
python3 "$profile_installer" --codex-home "$codex_home" --install
python3 "$profile_installer" --codex-home "$codex_home" --check
print "Bootstrap complete. Start a new Codex task to use the installed workflows."
