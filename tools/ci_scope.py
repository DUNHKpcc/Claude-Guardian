#!/usr/bin/env python3
"""Decide how wide the CI matrix runs for one push or pull request.

Docs-only changes (Markdown, PDF, PNG) run the Linux suite only; anything
else, or a range that cannot be read, runs the full three-platform matrix.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

DOC_SUFFIXES = (".md", ".pdf", ".png")
FULL = {"scope": "full", "os": ["ubuntu-latest", "macos-latest", "windows-latest"]}
DOCS = {"scope": "docs", "os": ["ubuntu-latest"]}


def classify(files: list[str]) -> dict:
    if not files:
        return FULL
    for name in files:
        if name.startswith(".github/") or not name.lower().endswith(DOC_SUFFIXES):
            return FULL
    return DOCS


def changed_files(base: str, head: str) -> list[str] | None:
    if not base or set(base) == {"0"}:
        return None
    result = subprocess.run(["git", "diff", "--name-only", base, head],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args(argv)
    files = changed_files(args.base, args.head)
    result = classify(files or [])
    print(f"scope={result['scope']} files={'unknown' if files is None else len(files)}", file=sys.stderr)
    out = os.environ.get("GITHUB_OUTPUT")
    lines = f"scope={result['scope']}\nos={json.dumps(result['os'])}\n"
    if out:
        with open(out, "a", encoding="utf-8") as handle:
            handle.write(lines)
    else:
        sys.stdout.write(lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
