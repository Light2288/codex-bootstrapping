#!/bin/zsh
# Run repository checks without reading or writing a user's Codex home.

emulate -LR zsh
setopt errexit nounset pipefail

script_dir=${0:A:h}
repository_root=${script_dir:h}
cd "$repository_root"

find_python_311() {
  local candidate candidate_path
  for candidate in python3.13 python3.12 python3.11 python3; do
    (( $+commands[$candidate] )) || continue
    candidate_path="$(whence -p "$candidate")"
    if "$candidate_path" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' 2>/dev/null; then
      print -r -- "$candidate_path"
      return 0
    fi
  done
  return 1
}

python_command="$(find_python_311)" || {
  print -u2 "Verification requires Python 3.11+ (for tomllib). Install Python 3.11 or newer and rerun scripts/verify.zsh."
  exit 1
}

zsh -n scripts/bootstrap-macos.zsh scripts/configure-provider.zsh scripts/verify.zsh
"$python_command" -m unittest discover -s tests -v
"$python_command" -m unittest discover -s plugins/personal-workflows/tests -v
"$python_command" -c '
import json
from pathlib import Path
root = Path(".")
marketplace = json.loads((root / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
manifest = json.loads((root / "plugins/personal-workflows/.codex-plugin/plugin.json").read_text(encoding="utf-8"))
assert marketplace["name"] == "personal"
assert marketplace["plugins"][0]["name"] == manifest["name"]
mapping = json.loads((root / "plugins/personal-workflows/references/integration-map.json").read_text(encoding="utf-8"))
assert mapping["wrappers"] and mapping["standalone"]
'
if rg -n --hidden --glob '!.git/**' --glob '!docs/**' --glob '!tests/**' '(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,}|xox[bp]-[A-Za-z0-9-]{20,})' .; then
  print -u2 "Likely credential found."
  exit 1
fi
print "Repository verification passed."
