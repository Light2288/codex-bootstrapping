#!/usr/bin/env python3
"""Verify the Superpowers dependencies required by the integration map."""

import argparse
import json
import re
from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[1]
INTEGRATION_MAP = PLUGIN / "references" / "integration-map.json"
FRONTMATTER_NAME = re.compile(r"^name:\s*([^\s#]+)\s*$", re.MULTILINE)


def skill_names(skills_root):
    """Return the declared names from immediate `skills/*/SKILL.md` files."""
    names = []
    for skill_file in sorted(skills_root.glob("*/SKILL.md")):
        match = FRONTMATTER_NAME.search(skill_file.read_text(encoding="utf-8"))
        if match:
            names.append(match.group(1).strip('"\''))
    return sorted(set(names))


def required_names():
    mapping = json.loads(INTEGRATION_MAP.read_text(encoding="utf-8"))
    return sorted({name for bases in mapping["wrappers"].values() for name in bases})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--superpowers-root", required=True, type=Path)
    args = parser.parse_args()

    available = skill_names(args.superpowers_root / "skills")
    required = required_names()
    personal = skill_names(PLUGIN / "skills")
    missing = sorted(set(required) - set(available))
    collisions = sorted(set(personal) & set(available))
    report = {
        "available": available,
        "required": required,
        "missing": missing,
        "collisions": collisions,
    }
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if missing or collisions else 0)


if __name__ == "__main__":
    main()
