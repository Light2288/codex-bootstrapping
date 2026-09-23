#!/usr/bin/env python3
"""Safely merge a custom Codex model provider into ``config.toml``.

This module deliberately has no API-key argument or setting.  The shell
wrapper stores a credential separately and asks this transformer to write
only non-secret provider metadata.
"""

from __future__ import print_function

import argparse
import datetime
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
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
_ENVIRONMENT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MANAGED_ROOT_KEYS = ("model", "model_reasoning_effort", "model_provider")
_REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}


@dataclass(frozen=True)
class _TableHeader:
    is_array: bool
    path: tuple


def _require_safe_text(name, value):
    if not isinstance(value, str) or not value or any(ord(character) < 32 for character in value):
        raise ValidationError("{0} must be non-empty text without control characters".format(name))


def validate_settings(settings):
    """Validate settings before they are rendered into TOML."""
    if not _PROVIDER_ID.match(settings.provider_id):
        raise ValidationError("provider ID may contain only letters, numbers, underscores, and hyphens")
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
    return re.compile(
        r"^(\s*" + re.escape(key) + r"\s*=\s*)(.*?)(\s*(?:#.*)?)(\r?\n?)$"
    )


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
            try:
                keys.append(json.loads(value[start:index]))
            except ValueError:
                return None
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
    for line in lines:
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

    for index, line in enumerate(lines):
        header = _parse_table_header(line)
        if header is not None:
            first_table = min(first_table, index)
            skip_selected_provider = _is_managed_provider_path(header, target_path)
            if skip_selected_provider:
                continue
        if skip_selected_provider:
            continue

        if index < first_table:
            did_replace = False
            for key, value in root_values.items():
                root_match = _root_assignment_pattern(key).match(line)
                if root_match:
                    kept_lines.append(root_match.group(1) + value + root_match.group(3) + root_match.group(4))
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
        while insertion_index < len(kept_lines):
            if _parse_table_header(kept_lines[insertion_index]) is not None:
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
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args(argv)

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
