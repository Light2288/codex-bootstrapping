#!/usr/bin/env python3
"""Report likely credential values in Git-tracked files without echoing them."""

from __future__ import print_function

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


LIKELY_CREDENTIAL = re.compile(
    rb"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|"
    rb"github_pat_[A-Za-z0-9_]{22,}|xox[bp]-[A-Za-z0-9-]{20,})(?!\w)"
)
INTENTIONAL_FIXTURES = {
    "tests/test_distribution.py": frozenset(
        (
            b"sk-" + b"abcdefghijklmnopqrstuvwxyz123456",
            b"ghp_" + b"abcdefghijklmnopqrstuvwxyz1234567890",
            b"github_pat_" + b"abcdefghijklmnopqrstuvwxyz",
            b"xoxb-" + b"1234567890-abcdefghijklmnopqrstuvwxyz",
        )
    )
}


def tracked_files(repository):
    """Return repository-relative paths from Git's index."""
    result = subprocess.run(
        ["git", "-C", str(repository), "ls-files", "-z"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError("could not list tracked files: {0}".format(message or "git failed"))
    return [os.fsdecode(path) for path in result.stdout.split(b"\0") if path]


def scan(repository):
    """Yield tracked path and line number for each non-allowlisted match."""
    repository = Path(repository)
    for relative_path in tracked_files(repository):
        path = repository / relative_path
        try:
            if path.is_symlink():
                content = os.fsencode(os.readlink(path))
            else:
                content = path.read_bytes()
        except FileNotFoundError:
            continue
        allowed = INTENTIONAL_FIXTURES.get(relative_path, ())
        for line_number, line in enumerate(content.splitlines(), 1):
            for match in LIKELY_CREDENTIAL.finditer(line):
                if match.group(0) not in allowed:
                    yield relative_path, line_number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args(argv)
    try:
        findings = list(scan(arguments.root))
    except (OSError, RuntimeError) as error:
        print("secret scan failed: {0}".format(error), file=sys.stderr)
        return 2
    for relative_path, line_number in findings:
        print(
            "Likely credential found in tracked file {0}:{1}".format(relative_path, line_number),
            file=sys.stderr,
        )
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
