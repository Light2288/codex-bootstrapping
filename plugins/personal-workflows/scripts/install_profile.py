#!/usr/bin/env python3
"""Safely install the personal-workflows global Codex profile."""

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path


START_MARKER = "<!-- personal-workflows:start -->"
END_MARKER = "<!-- personal-workflows:end -->"
MANAGED_AGENT_HEADER = "# Managed by personal-workflows\n"
MANAGED_AGENT_MODEL_ROLES = {
    "doc-analyst.toml": "full",
    "document-worker.toml": "full",
    "review-audit.toml": "full",
    "review-quality.toml": "full",
    "review-spec.toml": "light",
}


def merge_managed_block(existing: str, managed: str) -> str:
    """Replace the one managed block or append it without changing other text."""
    start_count = existing.count(START_MARKER)
    end_count = existing.count(END_MARKER)
    if start_count != end_count:
        raise ValueError("managed block markers are unmatched")
    if start_count > 1:
        raise ValueError("managed block markers are duplicated")

    if start_count == 0:
        separator = "" if not existing or existing.endswith(("\n", "\r")) else "\n"
        return f"{existing}{separator}{managed}"

    start = existing.index(START_MARKER)
    end = existing.index(END_MARKER)
    if end < start:
        raise ValueError("managed block end marker precedes its start marker")
    block_end = end + len(END_MARKER)
    if existing.startswith("\r\n", block_end):
        block_end += 2
    elif existing.startswith("\n", block_end):
        block_end += 1
    return f"{existing[:start]}{managed}{existing[block_end:]}"


def _extract_managed_models(existing: str):
    """Return supported routing overrides from the one owned guidance block."""
    if existing.count(START_MARKER) != 1 or existing.count(END_MARKER) != 1:
        return None
    start = existing.index(START_MARKER)
    end = existing.index(END_MARKER)
    if end < start:
        return None
    block = existing[start : end + len(END_MARKER)]
    models = {}
    for role in ("full", "light"):
        matches = re.findall(
            r"^- `" + role + r"`: `([^`]+)`\s*$", block, flags=re.MULTILINE
        )
        if len(matches) != 1:
            return None
        model = matches[0].rstrip("\r")
        if not model or any(ord(character) < 32 for character in model):
            return None
        models[role] = model
    return models


def _render_guidance_models(managed: str, models: dict) -> str:
    rendered = managed
    for role, model in models.items():
        rendered, count = re.subn(
            r"(?m)^(- `" + role + r"`: `)[^`]+(`\s*)$",
            lambda match: match.group(1) + model + match.group(2),
            rendered,
        )
        if count != 1:
            raise ValueError(f"packaged guidance has no unique {role} model")
    return rendered


def _toml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\b", "\\b").replace("\t", "\\t")
    escaped = escaped.replace("\n", "\\n").replace("\f", "\\f").replace("\r", "\\r")
    return f'"{escaped}"'


def _render_agent_model(source_contents: str, model: str) -> str:
    rendered, count = re.subn(
        r'(?m)^model\s*=\s*"[^"\\]*(?:\\.[^"\\]*)*"\s*$',
        lambda _match: "model = " + _toml_quote(model),
        source_contents,
    )
    if count != 1:
        raise ValueError("packaged agent has no unique root model assignment")
    return rendered


def _backup_existing(destination: Path):
    """Copy an existing destination to a collision-safe sibling backup."""
    if not destination.exists():
        return None

    sequence = 1
    while True:
        backup = destination.with_name(f"{destination.name}.backup.{sequence}")
        if not backup.exists():
            shutil.copyfile(destination, backup)
            return backup
        sequence += 1


def _replace_atomically(destination: Path, contents: str) -> None:
    """Back up an existing destination, then atomically replace it."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, delete=False
        ) as temporary_file:
            temporary_file.write(contents)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_path = Path(temporary_file.name)
        _backup_existing(destination)
        temporary_path.replace(destination)
    except Exception:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
        raise


def install_agent(
    source: Path,
    destination: Path,
    check_only: bool,
    source_contents: str = None,
) -> str:
    """Install one managed agent without replacing an unrelated destination."""
    if source_contents is None:
        source_contents = source.read_text(encoding="utf-8")
    if not destination.exists():
        if not check_only:
            _replace_atomically(destination, source_contents)
        return "would-create" if check_only else "created"

    destination_contents = destination.read_text(encoding="utf-8")
    if destination_contents == source_contents:
        return "unchanged"
    if not destination_contents.startswith(MANAGED_AGENT_HEADER):
        raise FileExistsError(f"refusing to replace unmanaged agent: {destination}")
    if not check_only:
        _replace_atomically(destination, source_contents)
    return "would-update" if check_only else "updated"


def install_profile(codex_home: Path, plugin_root: Path, check_only: bool) -> dict:
    """Install managed guidance and every canonical agent source in plugin_root."""
    managed_path = plugin_root / "profile" / "global-agents-block.md"
    agents_path = plugin_root / "codex-agents"
    guidance_path = codex_home / "AGENTS.md"
    managed = managed_path.read_text(encoding="utf-8")
    existing = guidance_path.read_text(encoding="utf-8") if guidance_path.exists() else ""
    active_models = _extract_managed_models(existing)
    if active_models is not None:
        managed = _render_guidance_models(managed, active_models)
    merged = merge_managed_block(existing, managed)
    guidance_status = "unchanged" if merged == existing else "would-update"
    sources = sorted(agents_path.glob("*.toml")) if agents_path.exists() else []
    destinations = [(source, codex_home / "agents" / source.name) for source in sources]

    rendered_sources = {}
    for source, _destination in destinations:
        contents = source.read_text(encoding="utf-8")
        role = MANAGED_AGENT_MODEL_ROLES.get(source.name)
        if active_models is not None and role is not None:
            contents = _render_agent_model(contents, active_models[role])
        rendered_sources[source] = contents
    planned_agents = {
        source.name: install_agent(
            source,
            destination,
            check_only=True,
            source_contents=rendered_sources[source],
        )
        for source, destination in destinations
    }
    if check_only:
        return {"guidance": guidance_status, "agents": planned_agents}

    if guidance_status != "unchanged":
        _replace_atomically(guidance_path, merged)
        guidance_status = "updated"
    installed_agents = {
        source.name: install_agent(
            source,
            destination,
            check_only=False,
            source_contents=rendered_sources[source],
        )
        for source, destination in destinations
    }
    return {"guidance": guidance_status, "agents": installed_agents}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--install", action="store_true")
    mode.add_argument("--check", action="store_true", dest="check_only")
    arguments = parser.parse_args()
    plugin_root = Path(__file__).resolve().parents[1]
    report = install_profile(arguments.codex_home, plugin_root, arguments.check_only)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
