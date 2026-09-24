#!/usr/bin/env python3
"""Safely merge a custom Codex model provider into ``config.toml``.

This module deliberately has no API-key argument or setting.  The shell
wrapper stores a credential separately and asks this transformer to write
only non-secret provider metadata.
"""

from __future__ import print_function

import argparse
import datetime
import os
import re
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


class ValidationError(ValueError):
    """Raised when a provider setting or managed TOML section is unsafe."""


@dataclass(frozen=True)
class ProviderSettings:
    provider_id: str
    display_name: str
    base_url: str
    model: str
    reasoning_effort: str
    wire_api: str
    credential_env_var: str
    supports_websockets: bool
    auth_mode: str


DEFAULT_SETTINGS = ProviderSettings(
    provider_id="ibm_ica",
    display_name="IBM ICA",
    base_url="https://api.servicesessentials.ibm.com/v1",
    model="gpt-5.6-sol",
    reasoning_effort="high",
    wire_api="responses",
    credential_env_var="IBM_ICA_CODEX_API_KEY",
    supports_websockets=False,
    auth_mode="keychain",
)


_PROVIDER_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_RESERVED_PROVIDER_IDS = {"openai", "ollama", "lmstudio"}
_ENVIRONMENT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MANAGED_ROOT_KEYS = ("model", "model_reasoning_effort", "model_provider")
_REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
_PROFILE_START_MARKER = "<!-- personal-workflows:start -->"
_PROFILE_END_MARKER = "<!-- personal-workflows:end -->"
_MANAGED_AGENT_HEADER = "# Managed by personal-workflows\n"
_MANAGED_AGENT_MODELS = {
    "doc-analyst.toml": "full",
    "document-worker.toml": "full",
    "review-audit.toml": "full",
    "review-quality.toml": "full",
    "review-spec.toml": "light",
}


@dataclass(frozen=True)
class _TableHeader:
    is_array: bool
    path: tuple


@dataclass(frozen=True)
class _LexedLine:
    text: str
    is_structural: bool
    multiline_after: Optional[str]


@dataclass(frozen=True)
class _ManagedFileState:
    path: Path
    content: bytes
    mode: int
    identity: tuple
    parent_identities: tuple


@dataclass(frozen=True)
class _ModelRoutingPlan:
    updates: dict
    states: dict


def _require_safe_text(name, value):
    if not isinstance(value, str) or not value or any(ord(character) < 32 for character in value):
        raise ValidationError("{0} must be non-empty text without control characters".format(name))


def validate_settings(settings):
    """Validate settings before they are rendered into TOML."""
    validate_provider_id(settings.provider_id)
    _require_safe_text("display name", settings.display_name)
    _require_safe_text("model", settings.model)
    parsed_url = urlparse(settings.base_url)
    if (
        parsed_url.scheme not in ("http", "https")
        or not parsed_url.netloc
        or any(character.isspace() for character in settings.base_url)
        or parsed_url.username is not None
        or parsed_url.password is not None
    ):
        raise ValidationError("base URL must be an http(s) URL with a host and no credentials")
    if settings.reasoning_effort not in _REASONING_EFFORTS:
        raise ValidationError("reasoning effort is not supported by this configurator")
    if settings.wire_api != "responses":
        raise ValidationError("wire API must be responses")
    if not _ENVIRONMENT_NAME.match(settings.credential_env_var):
        raise ValidationError("credential environment variable name is invalid")
    if not isinstance(settings.supports_websockets, bool):
        raise ValidationError("websocket support must be true or false")
    if settings.auth_mode not in ("keychain", "environment"):
        raise ValidationError("authentication mode must be keychain or environment")
    return settings


def validate_provider_id(provider_id):
    """Validate a provider identifier without reading or rendering configuration."""
    if not _PROVIDER_ID.match(provider_id):
        raise ValidationError("provider ID may contain only letters, numbers, underscores, and hyphens")
    if provider_id in _RESERVED_PROVIDER_IDS:
        raise ValidationError("provider ID is reserved by Codex")
    return provider_id


def toml_quote(value):
    """Return a TOML basic string without treating user text as TOML syntax."""
    _require_safe_text("TOML value", value)
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\b", "\\b").replace("\t", "\\t")
    escaped = escaped.replace("\n", "\\n").replace("\f", "\\f").replace("\r", "\\r")
    return '"{0}"'.format(escaped)


def _provider_table(settings):
    value = settings.provider_id
    lines = [
        "[model_providers.{0}]\n".format(value),
        "name = {0}\n".format(toml_quote(settings.display_name)),
        "base_url = {0}\n".format(toml_quote(settings.base_url)),
        "wire_api = \"responses\"\n",
        "supports_websockets = {0}\n".format(str(settings.supports_websockets).lower()),
    ]
    if settings.auth_mode == "environment":
        lines.append("env_key = {0}\n".format(toml_quote(settings.credential_env_var)))
    else:
        service = "codex-provider-{0}".format(value)
        lines.extend(
            [
                "\n",
                "[model_providers.{0}.auth]\n".format(value),
                'command = "/usr/bin/security"\n',
                "args = [\"find-generic-password\", \"-s\", {0}, \"-a\", \"codex\", \"-w\"]\n".format(
                    toml_quote(service)
                ),
                "timeout_ms = 5000\n",
                "refresh_interval_ms = 0\n",
            ]
        )
    return lines


def _root_assignment_pattern(key):
    key_syntax = r"(?:{0}|\"{0}\"|'{0}')".format(re.escape(key))
    return re.compile(
        r"^(\s*" + key_syntax + r"\s*=\s*)(.*?)(\s*(?:#.*)?)(\r?\n?)$"
    )


def _multiline_state_after(line, state):
    """Track multiline strings while ignoring delimiters in comments and single-line strings."""
    index = 0
    while index < len(line):
        if state == "basic":
            if line.startswith('"""', index):
                state = None
                index += 3
            elif line[index] == "\\":
                index += 2
            else:
                index += 1
            continue
        if state == "literal":
            if line.startswith("'''", index):
                state = None
                index += 3
            else:
                index += 1
            continue

        character = line[index]
        if character == "#":
            break
        if line.startswith('"""', index):
            state = "basic"
            index += 3
            continue
        if line.startswith("'''", index):
            state = "literal"
            index += 3
            continue
        if character == '"':
            index += 1
            while index < len(line):
                if line[index] == "\\":
                    index += 2
                elif line[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            continue
        if character == "'":
            closing_quote = line.find("'", index + 1)
            index = len(line) if closing_quote < 0 else closing_quote + 1
            continue
        index += 1
    return state


def _lex_toml_lines(lines):
    state = None
    lexed = []
    for line in lines:
        is_structural = state is None
        state = _multiline_state_after(line, state)
        lexed.append(_LexedLine(line, is_structural, state))
    return lexed


def _decode_toml_basic_key(value):
    """Decode a single-line TOML basic string used as a table key."""
    if len(value) < 2 or value[0] != '"' or value[-1] != '"':
        return None
    escaped_values = {
        "b": "\b",
        "t": "\t",
        "n": "\n",
        "f": "\f",
        "r": "\r",
        '"': '"',
        "\\": "\\",
    }
    output = []
    index = 1
    end = len(value) - 1
    while index < end:
        character = value[index]
        if character != "\\":
            if ord(character) < 32:
                return None
            output.append(character)
            index += 1
            continue
        index += 1
        if index == end:
            return None
        escape = value[index]
        if escape in escaped_values:
            output.append(escaped_values[escape])
            index += 1
            continue
        if escape not in ("u", "U"):
            return None
        digits = 4 if escape == "u" else 8
        hexadecimal = value[index + 1 : index + 1 + digits]
        if len(hexadecimal) != digits or not re.match(r"^[0-9A-Fa-f]+$", hexadecimal):
            return None
        codepoint = int(hexadecimal, 16)
        if codepoint > 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
            return None
        output.append(chr(codepoint))
        index += digits + 1
    return "".join(output)


def _parse_toml_string_value(value):
    value = value.strip()
    if value.startswith('"'):
        return _decode_toml_basic_key(value)
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'" and "'" not in value[1:-1]:
        return value[1:-1]
    return None


def _parse_dotted_keys(value):
    """Parse the TOML table-key subset needed to identify managed tables."""
    index = 0
    keys = []
    length = len(value)
    while index < length:
        while index < length and value[index].isspace():
            index += 1
        if index == length:
            return None
        if value[index] == '"':
            start = index
            index += 1
            escaped = False
            while index < length:
                character = value[index]
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    index += 1
                    break
                index += 1
            else:
                return None
            decoded = _decode_toml_basic_key(value[start:index])
            if decoded is None:
                return None
            keys.append(decoded)
        elif value[index] == "'":
            index += 1
            start = index
            while index < length and value[index] != "'":
                index += 1
            if index == length:
                return None
            keys.append(value[start:index])
            index += 1
        else:
            matched = re.match(r"[A-Za-z0-9_-]+", value[index:])
            if not matched:
                return None
            keys.append(matched.group(0))
            index += len(matched.group(0))

        while index < length and value[index].isspace():
            index += 1
        if index == length:
            return tuple(keys)
        if value[index] != ".":
            return None
        index += 1
    return None


def _parse_table_header(line):
    """Return a parsed TOML table header, or ``None`` when the line is not one."""
    source = line.rstrip("\r\n")
    position = 0
    while position < len(source) and source[position].isspace():
        position += 1
    if not source.startswith("[", position):
        return None

    is_array = source.startswith("[[", position)
    position += 2 if is_array else 1
    start = position
    quote = None
    escaped = False
    while position < len(source):
        character = source[position]
        if quote is not None:
            if quote == '"' and escaped:
                escaped = False
            elif quote == '"' and character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            position += 1
            continue
        if character in ("'", '"'):
            quote = character
            position += 1
            continue
        if is_array and source.startswith("]]", position):
            end = position
            position += 2
            break
        if not is_array and character == "]":
            end = position
            position += 1
            break
        position += 1
    else:
        return None

    remainder = source[position:]
    if not re.match(r"^\s*(?:#.*)?$", remainder):
        return None
    raw_path = source[start:end]
    return _TableHeader(is_array, _parse_dotted_keys(raw_path))


def _is_managed_provider_path(header, target_path):
    if header.path is None:
        raise ValidationError("table header uses unsupported TOML key syntax")
    return header.path[: len(target_path)] == target_path


def _validate_managed_toml(lines, provider_id):
    root_section = True
    root_counts = {key: 0 for key in _MANAGED_ROOT_KEYS}
    table_counts = {}
    target_path = ("model_providers", provider_id)
    for lexed_line in _lex_toml_lines(lines):
        if not lexed_line.is_structural:
            continue
        line = lexed_line.text
        stripped = line.lstrip()
        if stripped.startswith("["):
            header = _parse_table_header(line)
            if header is None:
                raise ValidationError("malformed TOML table header")
            root_section = False
            if _is_managed_provider_path(header, target_path):
                if header.is_array:
                    raise ValidationError("managed provider cannot be an array table")
                table_counts[header.path] = table_counts.get(header.path, 0) + 1
                if table_counts[header.path] > 1:
                    raise ValidationError("managed provider table appears more than once")
            continue
        if root_section:
            for key in _MANAGED_ROOT_KEYS:
                if _root_assignment_pattern(key).match(line):
                    root_counts[key] += 1
                    if root_counts[key] > 1:
                        raise ValidationError("managed root key appears more than once")


def _validate_toml_if_available(content):
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        return
    try:
        tomllib.loads(content)
    except Exception as error:
        raise ValidationError("configuration is not valid TOML: {0}".format(error))


def _validate_toml_required(content):
    """Parse TOML for models-only updates or refuse to plan any write."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        raise ValidationError("models-only updates require Python 3.11 or newer")
    try:
        tomllib.loads(content)
    except Exception as error:
        raise ValidationError("managed target is not valid TOML: {0}".format(error))


def merge_config(existing, settings):
    """Merge managed settings while retaining all unrelated text verbatim."""
    validate_settings(settings)
    lines = existing.splitlines(keepends=True)
    _validate_managed_toml(lines, settings.provider_id)
    _validate_toml_if_available(existing)

    first_table = len(lines)
    target_path = ("model_providers", settings.provider_id)
    kept_lines = []
    root_values = {
        "model": toml_quote(settings.model),
        "model_reasoning_effort": toml_quote(settings.reasoning_effort),
        "model_provider": toml_quote(settings.provider_id),
    }
    replaced_roots = set()
    skip_selected_provider = False

    skip_replaced_multiline = False
    for index, lexed_line in enumerate(_lex_toml_lines(lines)):
        line = lexed_line.text
        if skip_replaced_multiline:
            if lexed_line.multiline_after is None:
                skip_replaced_multiline = False
            continue

        header = _parse_table_header(line) if lexed_line.is_structural else None
        if header is not None:
            first_table = min(first_table, index)
            skip_selected_provider = _is_managed_provider_path(header, target_path)
            if skip_selected_provider:
                continue
        if skip_selected_provider:
            continue

        if index < first_table and lexed_line.is_structural:
            did_replace = False
            for key, value in root_values.items():
                root_match = _root_assignment_pattern(key).match(line)
                if root_match:
                    if lexed_line.multiline_after is None:
                        kept_lines.append(root_match.group(1) + value + root_match.group(3) + root_match.group(4))
                    else:
                        kept_lines.append(root_match.group(1) + value + root_match.group(4))
                        skip_replaced_multiline = True
                    replaced_roots.add(key)
                    did_replace = True
                    break
            if did_replace:
                continue
        kept_lines.append(line)

    missing_root_lines = [
        "{0} = {1}\n".format(key, value)
        for key, value in root_values.items()
        if key not in replaced_roots
    ]
    if missing_root_lines:
        insertion_index = 0
        lexed_kept_lines = _lex_toml_lines(kept_lines)
        while insertion_index < len(lexed_kept_lines):
            lexed_line = lexed_kept_lines[insertion_index]
            if lexed_line.is_structural and _parse_table_header(lexed_line.text) is not None:
                break
            insertion_index += 1
        kept_lines[insertion_index:insertion_index] = missing_root_lines

    if kept_lines and kept_lines[-1] and not kept_lines[-1].endswith("\n"):
        kept_lines[-1] += "\n"
    if kept_lines and (not kept_lines[-1].strip()):
        pass
    elif kept_lines:
        kept_lines.append("\n")
    kept_lines.extend(_provider_table(settings))
    rendered = "".join(kept_lines)
    _validate_toml_if_available(rendered)
    return rendered


def preview_config(settings):
    """Render a redacted preview.  Settings never contain a credential."""
    validate_settings(settings)
    storage = "macOS Keychain" if settings.auth_mode == "keychain" else "environment variable"
    return "Credential storage: {0}\n\n{1}".format(storage, merge_config("", settings))


def atomic_write_config(target, content):
    """Back up an existing config and replace it atomically with validated content."""
    target = Path(target)
    _validate_toml_if_available(content)
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if target.exists():
        stamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        backup = target.with_name("{0}.backup.{1}".format(target.name, stamp))
        shutil.copy2(str(target), str(backup))

    descriptor, temporary_name = tempfile.mkstemp(prefix=".{0}.".format(target.name), dir=str(target.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        if target.exists():
            os.chmod(temporary_name, target.stat().st_mode & 0o777)
        os.replace(temporary_name, str(target))
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
    return backup


def _validate_model_name(role, value):
    _require_safe_text("{0} model".format(role), value)
    if "`" in value:
        raise ValidationError("{0} model cannot contain a backtick".format(role))
    return value


def _owned_regular_file(path, label, codex_home):
    if path.is_symlink():
        raise ValidationError("refusing symlinked {0}: {1}".format(label, path))
    if not path.is_file():
        raise ValidationError("missing managed {0}: {1}".format(label, path))
    try:
        path.resolve().relative_to(Path(codex_home).resolve())
    except ValueError:
        raise ValidationError("refusing {0} outside the Codex home: {1}".format(label, path))


def _directory_identity(path):
    status = os.lstat(str(path))
    if not stat.S_ISDIR(status.st_mode) or stat.S_ISLNK(status.st_mode):
        raise ValidationError("managed target parent is not a real directory: {0}".format(path))
    return (status.st_dev, status.st_ino, status.st_mode)


def _file_identity(path):
    status = os.lstat(str(path))
    if not stat.S_ISREG(status.st_mode) or stat.S_ISLNK(status.st_mode):
        raise ValidationError("managed target is not a regular file: {0}".format(path))
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _parent_identities(path, codex_home):
    codex_home = Path(codex_home).resolve()
    try:
        relative_parent = path.parent.relative_to(codex_home)
    except ValueError:
        raise ValidationError("refusing managed target outside the Codex home: {0}".format(path))
    current = codex_home
    identities = [(current, _directory_identity(current))]
    for part in relative_parent.parts:
        current = current / part
        identities.append((current, _directory_identity(current)))
    return tuple(identities)


def _read_stable_managed_file(path, label, codex_home):
    _owned_regular_file(path, label, codex_home)
    parents_before = _parent_identities(path, codex_home)
    identity_before = _file_identity(path)
    content = path.read_bytes()
    parents_after = _parent_identities(path, codex_home)
    identity_after = _file_identity(path)
    if parents_after != parents_before or identity_after != identity_before:
        raise ValidationError("managed target changed while it was being read: {0}".format(path))
    return _ManagedFileState(
        path=path,
        content=content,
        mode=identity_before[2] & 0o777,
        identity=identity_before,
        parent_identities=parents_before,
    )


def _assert_parent_identities(state):
    try:
        current = tuple(
            (path, _directory_identity(path)) for path, _identity in state.parent_identities
        )
    except (OSError, ValidationError):
        raise ValidationError("managed target parent changed during update: {0}".format(state.path))
    if current != state.parent_identities:
        raise ValidationError("managed target parent changed during update: {0}".format(state.path))


def _assert_managed_file_unchanged(state):
    _assert_parent_identities(state)
    try:
        current = _file_identity(state.path)
    except (OSError, ValidationError):
        raise ValidationError("managed target changed during update: {0}".format(state.path))
    if current != state.identity:
        raise ValidationError("managed target changed during update: {0}".format(state.path))


def _replace_single_root_assignment(existing, key, value, label):
    lines = existing.splitlines(keepends=True)
    lexed_lines = _lex_toml_lines(lines)
    matches = []
    root_section = True
    for index, lexed_line in enumerate(lexed_lines):
        if not lexed_line.is_structural:
            continue
        stripped = lexed_line.text.lstrip()
        header = _parse_table_header(lexed_line.text)
        if stripped.startswith("[") and header is None:
            raise ValidationError("managed {0} contains a malformed table header".format(label))
        if header is not None:
            root_section = False
        if root_section:
            match = _root_assignment_pattern(key).match(lexed_line.text)
            if match:
                matches.append((index, match))
    if len(matches) != 1:
        raise ValidationError(
            "managed {0} must contain exactly one top-level {1} assignment".format(
                label, key
            )
        )
    index, match = matches[0]
    if lexed_lines[index].multiline_after is not None:
        raise ValidationError("managed {0} has a multiline {1}".format(label, key))
    current_value = _parse_toml_string_value(match.group(2))
    if current_value is None or not current_value:
        raise ValidationError("managed {0} has a malformed {1}".format(label, key))
    lines[index] = match.group(1) + toml_quote(value) + match.group(3) + match.group(4)
    rendered = "".join(lines)
    _validate_toml_if_available(rendered)
    return rendered


def _replace_managed_guidance(existing, full_model, light_model):
    if existing.count(_PROFILE_START_MARKER) != 1 or existing.count(_PROFILE_END_MARKER) != 1:
        raise ValidationError("managed personal-workflows guidance markers are missing or duplicated")
    start = existing.index(_PROFILE_START_MARKER)
    end = existing.index(_PROFILE_END_MARKER)
    if end < start:
        raise ValidationError("managed personal-workflows guidance markers are reversed")
    block_end = end + len(_PROFILE_END_MARKER)
    block = existing[start:block_end]
    replacements = {"full": full_model, "light": light_model}
    for role, model in replacements.items():
        pattern = re.compile(
            r"^(\s*-\s*`" + role + r"`:\s*`)([^`]*)(`\s*)$", re.MULTILINE
        )
        matches = list(pattern.finditer(block))
        if len(matches) != 1:
            raise ValidationError(
                "managed personal-workflows guidance must contain exactly one {0} model".format(
                    role
                )
            )
        block = pattern.sub(lambda match: match.group(1) + model + match.group(3), block)
    return existing[:start] + block + existing[block_end:]


def _validate_agent_identity(existing, expected_name, path):
    if not existing.startswith(_MANAGED_AGENT_HEADER):
        raise ValidationError("refusing unmanaged agent: {0}".format(path))
    name_pattern = _root_assignment_pattern("name")
    names = []
    root_section = True
    for lexed_line in _lex_toml_lines(existing.splitlines(keepends=True)):
        if not lexed_line.is_structural:
            continue
        if _parse_table_header(lexed_line.text) is not None:
            root_section = False
        if root_section:
            match = name_pattern.match(lexed_line.text)
            if match:
                names.append(_parse_toml_string_value(match.group(2)))
    if names != [expected_name]:
        raise ValidationError("managed agent identity is malformed: {0}".format(path))
    _validate_toml_if_available(existing)


def _build_model_routing_plan(codex_home, full_model, light_model):
    """Read, validate, and snapshot the complete ownership-bounded update."""
    codex_home = Path(codex_home).resolve()
    full_model = _validate_model_name("full", full_model)
    light_model = _validate_model_name("light", light_model)
    config_path = codex_home / "config.toml"
    guidance_path = codex_home / "AGENTS.md"
    states = {
        config_path: _read_stable_managed_file(config_path, "config", codex_home),
        guidance_path: _read_stable_managed_file(guidance_path, "guidance", codex_home),
    }
    try:
        originals = {
            path: state.content.decode("utf-8") for path, state in states.items()
        }
    except UnicodeDecodeError as error:
        raise ValidationError("managed target is not UTF-8 text: {0}".format(error))
    _validate_toml_required(originals[config_path])
    rendered = {
        config_path: _replace_single_root_assignment(
            originals[config_path], "model", full_model, "config"
        ),
        guidance_path: _replace_managed_guidance(
            originals[guidance_path], full_model, light_model
        ),
    }
    for filename, role in sorted(_MANAGED_AGENT_MODELS.items()):
        path = codex_home / "agents" / filename
        state = _read_stable_managed_file(path, "agent", codex_home)
        states[path] = state
        try:
            existing = state.content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValidationError("managed agent is not UTF-8 text: {0}".format(error))
        _validate_toml_required(existing)
        _validate_agent_identity(existing, filename[:-5], path)
        model = full_model if role == "full" else light_model
        originals[path] = existing
        rendered[path] = _replace_single_root_assignment(existing, "model", model, "agent")
    updates = {
        path: contents
        for path, contents in rendered.items()
        if contents != originals[path]
    }
    for path, contents in updates.items():
        if path.suffix == ".toml":
            _validate_toml_required(contents)
    return _ModelRoutingPlan(updates=updates, states=states)


def plan_model_routing_update(codex_home, full_model, light_model):
    """Validate and render the complete ownership-bounded routing update."""
    return _build_model_routing_plan(codex_home, full_model, light_model).updates


def _open_model_routing_directories(codex_home):
    required = ("O_DIRECTORY", "O_NOFOLLOW")
    if any(not hasattr(os, name) for name in required):
        raise ValidationError("models-only updates require no-follow directory support")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root = Path(codex_home).resolve()
    root_descriptor = os.open(str(root), flags)
    try:
        agents_descriptor = os.open("agents", flags, dir_fd=root_descriptor)
    except Exception:
        os.close(root_descriptor)
        raise
    return {
        root: root_descriptor,
        root / "agents": agents_descriptor,
    }


def _close_model_routing_directories(directory_descriptors):
    for descriptor in reversed(list(directory_descriptors.values())):
        os.close(descriptor)


def _directory_descriptor_for(state, directory_descriptors):
    try:
        descriptor = directory_descriptors[state.path.parent]
    except KeyError:
        raise ValidationError("managed target parent is not approved: {0}".format(state.path))
    expected = dict(state.parent_identities)[state.path.parent]
    status = os.fstat(descriptor)
    current = (status.st_dev, status.st_ino, status.st_mode)
    if current != expected:
        raise ValidationError("managed target parent changed during update: {0}".format(state.path))
    return descriptor


def _file_identity_from_descriptor(descriptor):
    status = os.fstat(descriptor)
    if not stat.S_ISREG(status.st_mode):
        raise ValidationError("managed target is no longer a regular file")
    return (
        status.st_dev,
        status.st_ino,
        status.st_mode,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _open_verified_file_at(directory_descriptor, state):
    flags = os.O_RDONLY | os.O_NOFOLLOW
    descriptor = os.open(state.path.name, flags, dir_fd=directory_descriptor)
    try:
        if _file_identity_from_descriptor(descriptor) != state.identity:
            raise ValidationError("managed target changed during update: {0}".format(state.path))
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _create_temporary_file_at(directory_descriptor, prefix):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    for _attempt in range(100):
        name = ".{0}.{1}".format(prefix, next(tempfile._get_candidate_names()))
        try:
            descriptor = os.open(name, flags, 0o600, dir_fd=directory_descriptor)
        except FileExistsError:
            continue
        return name, descriptor
    raise OSError("could not allocate a collision-safe temporary file")


def _write_all(descriptor, content):
    view = memoryview(content)
    while view:
        written = os.write(descriptor, view)
        if written == 0:
            raise OSError("short write while updating managed model routing")
        view = view[written:]


def _collision_safe_backup_at(directory_descriptor, state):
    sequence = 1
    while True:
        backup_name = "{0}.backup.{1}".format(state.path.name, sequence)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        try:
            backup_descriptor = os.open(
                backup_name,
                flags,
                state.mode,
                dir_fd=directory_descriptor,
            )
        except FileExistsError:
            sequence += 1
            continue
        source_descriptor = None
        try:
            source_descriptor = _open_verified_file_at(directory_descriptor, state)
            while True:
                chunk = os.read(source_descriptor, 1024 * 1024)
                if not chunk:
                    break
                _write_all(backup_descriptor, chunk)
            os.fchmod(backup_descriptor, state.mode)
            os.fsync(backup_descriptor)
        except Exception:
            try:
                os.unlink(backup_name, dir_fd=directory_descriptor)
            except OSError:
                pass
            raise
        finally:
            if source_descriptor is not None:
                os.close(source_descriptor)
            os.close(backup_descriptor)
        return state.path.with_name(backup_name)


def _atomic_replace_content_at(directory_descriptor, state, content):
    source_descriptor = _open_verified_file_at(directory_descriptor, state)
    os.close(source_descriptor)
    temporary_name, temporary_descriptor = _create_temporary_file_at(
        directory_descriptor, state.path.name
    )
    try:
        _write_all(temporary_descriptor, content.encode("utf-8"))
        os.fchmod(temporary_descriptor, state.mode)
        os.fsync(temporary_descriptor)
        os.close(temporary_descriptor)
        temporary_descriptor = None
        os.replace(
            temporary_name,
            state.path.name,
            src_dir_fd=directory_descriptor,
            dst_dir_fd=directory_descriptor,
        )
    except Exception:
        if temporary_descriptor is not None:
            os.close(temporary_descriptor)
        try:
            os.unlink(temporary_name, dir_fd=directory_descriptor)
        except OSError:
            pass
        raise


def _atomic_restore_bytes_at(directory_descriptor, state):
    temporary_name, temporary_descriptor = _create_temporary_file_at(
        directory_descriptor, "{0}.rollback".format(state.path.name)
    )
    try:
        _write_all(temporary_descriptor, state.content)
        os.fchmod(temporary_descriptor, state.mode)
        os.fsync(temporary_descriptor)
        os.close(temporary_descriptor)
        temporary_descriptor = None
        os.replace(
            temporary_name,
            state.path.name,
            src_dir_fd=directory_descriptor,
            dst_dir_fd=directory_descriptor,
        )
    except Exception:
        if temporary_descriptor is not None:
            os.close(temporary_descriptor)
        try:
            os.unlink(temporary_name, dir_fd=directory_descriptor)
        except OSError:
            pass
        raise


def _acquire_model_routing_lock(codex_home):
    lock_path = Path(codex_home).resolve() / ".provider-model-routing.lock"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(str(lock_path), flags, 0o600)
    except FileExistsError:
        raise ValidationError("another models-only update is already active")
    status = os.fstat(descriptor)
    return lock_path, descriptor, (status.st_dev, status.st_ino)


def _release_model_routing_lock(lock_path, descriptor, identity):
    os.close(descriptor)
    try:
        status = os.lstat(str(lock_path))
    except FileNotFoundError:
        return
    if (status.st_dev, status.st_ino) == identity and stat.S_ISREG(status.st_mode):
        os.unlink(str(lock_path))


def apply_model_routing_update(codex_home, full_model, light_model):
    """Back up and atomically apply one validated multi-file routing transaction."""
    codex_home = Path(codex_home).resolve()
    lock_path, lock_descriptor, lock_identity = _acquire_model_routing_lock(codex_home)
    directory_descriptors = None
    try:
        directory_descriptors = _open_model_routing_directories(codex_home)
        plan = _build_model_routing_plan(codex_home, full_model, light_model)
        updates = plan.updates
        backups = {}
        for path in updates:
            state = plan.states[path]
            _assert_managed_file_unchanged(state)
            directory_descriptor = _directory_descriptor_for(
                state, directory_descriptors
            )
            backups[path] = _collision_safe_backup_at(directory_descriptor, state)
            _assert_parent_identities(state)
        replaced = []
        try:
            for path, content in updates.items():
                state = plan.states[path]
                _assert_managed_file_unchanged(state)
                directory_descriptor = _directory_descriptor_for(
                    state, directory_descriptors
                )
                _atomic_replace_content_at(directory_descriptor, state, content)
                replaced.append(path)
                _assert_parent_identities(state)
        except Exception as error:
            try:
                for path in reversed(replaced):
                    state = plan.states[path]
                    directory_descriptor = _directory_descriptor_for(
                        state, directory_descriptors
                    )
                    _atomic_restore_bytes_at(directory_descriptor, state)
            except Exception as rollback_error:
                raise OSError(
                    "model routing update failed and rollback was incomplete: {0}".format(
                        rollback_error
                    )
                ) from error
            raise
        return backups
    finally:
        if directory_descriptors is not None:
            _close_model_routing_directories(directory_descriptors)
        _release_model_routing_lock(lock_path, lock_descriptor, lock_identity)


def _settings_from_arguments(arguments):
    return ProviderSettings(
        provider_id=arguments.provider_id,
        display_name=arguments.display_name,
        base_url=arguments.base_url,
        model=arguments.model,
        reasoning_effort=arguments.reasoning_effort,
        wire_api=arguments.wire_api,
        credential_env_var=arguments.credential_env_var,
        supports_websockets=arguments.supports_websockets == "true",
        auth_mode=arguments.auth_mode,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    default_config = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    parser.add_argument("--config", type=Path, default=default_config)
    parser.add_argument("--provider-id", default=DEFAULT_SETTINGS.provider_id)
    parser.add_argument("--display-name", default=DEFAULT_SETTINGS.display_name)
    parser.add_argument("--base-url", default=DEFAULT_SETTINGS.base_url)
    parser.add_argument("--model", default=DEFAULT_SETTINGS.model)
    parser.add_argument("--reasoning-effort", default=DEFAULT_SETTINGS.reasoning_effort)
    parser.add_argument("--wire-api", default=DEFAULT_SETTINGS.wire_api)
    parser.add_argument("--credential-env-var", default=DEFAULT_SETTINGS.credential_env_var)
    parser.add_argument("--supports-websockets", choices=("true", "false"), default="false")
    parser.add_argument("--auth-mode", choices=("keychain", "environment"), default="keychain")
    parser.add_argument("--models-only", action="store_true")
    parser.add_argument("--full-model", default="gpt-5.6-sol")
    parser.add_argument("--light-model", default="gpt-5.6-luna")
    parser.add_argument("--validate-provider-id")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args(argv)

    if arguments.validate_provider_id is not None:
        if arguments.models_only or arguments.check or arguments.dry_run:
            parser.error("--validate-provider-id cannot be combined with another mode")
        validate_provider_id(arguments.validate_provider_id)
        return 0

    if arguments.models_only:
        updates = plan_model_routing_update(
            arguments.config.parent,
            arguments.full_model,
            arguments.light_model,
        )
        if arguments.check:
            print("check: managed model routing is valid; no files were changed")
            return 0
        if arguments.dry_run:
            print("dry-run: would update managed model routing under {0}".format(arguments.config.parent))
            print("full model: {0}".format(arguments.full_model))
            print("light model: {0}".format(arguments.light_model))
            for path in updates:
                print("would update {0}".format(path))
            return 0
        backups = apply_model_routing_update(
            arguments.config.parent,
            arguments.full_model,
            arguments.light_model,
        )
        if backups:
            print("updated managed model routing; backups:")
            for backup in backups.values():
                print(backup)
        else:
            print("managed model routing is already current")
        return 0

    settings = _settings_from_arguments(arguments)
    existing = arguments.config.read_text(encoding="utf-8") if arguments.config.exists() else ""
    rendered = merge_config(existing, settings)
    if arguments.check:
        print("check: configuration is valid; no files were changed")
        return 0
    if arguments.dry_run:
        print("dry-run: would update {0}".format(arguments.config))
        print(preview_config(settings), end="")
        return 0
    backup = atomic_write_config(arguments.config, rendered)
    if backup is None:
        print("updated {0}".format(arguments.config))
    else:
        print("updated {0}; backup: {1}".format(arguments.config, backup))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValidationError) as error:
        print("provider configuration failed: {0}".format(error), file=sys.stderr)
        sys.exit(1)
