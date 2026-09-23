#!/usr/bin/env python3
"""Safely remove the global profile managed by personal-workflows."""

from __future__ import print_function

import argparse
import json
import shutil
import tempfile
from pathlib import Path


START_MARKER = "<!-- personal-workflows:start -->"
END_MARKER = "<!-- personal-workflows:end -->"
MANAGED_AGENT_HEADER = "# Managed by personal-workflows\n"


def remove_managed_block(existing):
    """Remove exactly one managed guidance block without changing other text."""
    start_count = existing.count(START_MARKER)
    end_count = existing.count(END_MARKER)
    if start_count != end_count:
        raise ValueError("managed block markers are unmatched")
    if start_count > 1:
        raise ValueError("managed block markers are duplicated")
    if not start_count:
        return existing, "absent"

    start = existing.index(START_MARKER)
    end = existing.index(END_MARKER)
    if end < start:
        raise ValueError("managed block end marker precedes its start marker")
    block_end = end + len(END_MARKER)
    if existing.startswith("\r\n", block_end):
        block_end += 2
    elif existing.startswith("\n", block_end):
        block_end += 1
    return existing[:start] + existing[block_end:], "would-remove"


def managed_agent_names(plugin_root):
    """Return the canonical global-agent names distributed by this plugin."""
    return sorted(path.name for path in (plugin_root / "codex-agents").glob("*.toml"))


def plan_uninstall(codex_home, plugin_root):
    """Validate ownership first, then describe the safe profile removal."""
    guidance_path = codex_home / "AGENTS.md"
    guidance_text = guidance_path.read_text(encoding="utf-8") if guidance_path.exists() else ""
    remaining_guidance, guidance_status = remove_managed_block(guidance_text)
    agents_directory = codex_home / "agents"
    agents = {}
    removals = []
    for name in managed_agent_names(plugin_root):
        destination = agents_directory / name
        if not destination.exists():
            agents[name] = "absent"
            continue
        contents = destination.read_text(encoding="utf-8")
        if not contents.startswith(MANAGED_AGENT_HEADER):
            raise FileExistsError("refusing to remove unmanaged agent: {0}".format(destination))
        agents[name] = "would-remove"
        removals.append(destination)
    return {
        "guidance_path": guidance_path,
        "remaining_guidance": remaining_guidance,
        "guidance": guidance_status,
        "agents": agents,
        "removals": removals,
    }


def _stage_path(path, codex_home, quarantine):
    """Atomically move one managed artifact into the transaction quarantine."""
    staged_path = quarantine / path.relative_to(codex_home)
    staged_path.parent.mkdir(parents=True, exist_ok=True)
    path.replace(staged_path)


def _restore_quarantine(quarantine, paths, codex_home, original_contents):
    """Move every staged artifact back to its original location after a failure."""
    for path in reversed(paths):
        staged_path = quarantine / path.relative_to(codex_home)
        if staged_path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.replace(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(original_contents[path])
    if quarantine.exists():
        try:
            shutil.rmtree(str(quarantine))
        except OSError:
            pass


def _delete_quarantine(quarantine):
    """Permanently remove a fully staged profile only after every move succeeds."""
    shutil.rmtree(str(quarantine))


def uninstall_profile(codex_home, plugin_root, check_only):
    """Remove validated personal-workflows artifacts, or report the planned removal."""
    plan = plan_uninstall(codex_home, plugin_root)
    if check_only:
        return {"guidance": plan["guidance"], "agents": plan["agents"]}

    paths = list(plan["removals"])
    if plan["guidance"] == "would-remove":
        paths.insert(0, plan["guidance_path"])
    if not paths:
        return {"guidance": plan["guidance"], "agents": plan["agents"]}

    original_contents = {path: path.read_bytes() for path in paths}
    quarantine = Path(tempfile.mkdtemp(prefix=".personal-workflows-uninstall-", dir=str(codex_home)))
    staged_paths = []
    try:
        if plan["guidance"] == "would-remove":
            _stage_path(plan["guidance_path"], codex_home, quarantine)
            staged_paths.append(plan["guidance_path"])
            plan["guidance_path"].write_text(plan["remaining_guidance"], encoding="utf-8")
        for path in plan["removals"]:
            _stage_path(path, codex_home, quarantine)
            staged_paths.append(path)
        _delete_quarantine(quarantine)
    except OSError:
        _restore_quarantine(quarantine, staged_paths, codex_home, original_contents)
        raise

    if plan["guidance"] == "would-remove":
        plan["guidance"] = "removed"
    for destination in plan["removals"]:
        plan["agents"][destination.name] = "removed"
    return {"guidance": plan["guidance"], "agents": plan["agents"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--uninstall", action="store_true")
    mode.add_argument("--check", action="store_true", dest="check_only")
    arguments = parser.parse_args()
    plugin_root = Path(__file__).resolve().parents[1] / "plugins" / "personal-workflows"
    try:
        report = uninstall_profile(arguments.codex_home, plugin_root, arguments.check_only)
    except (OSError, ValueError) as error:
        print(str(error), file=__import__("sys").stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
