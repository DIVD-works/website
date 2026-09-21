#!/usr/bin/env python3
"""Check the static site's lightweight performance budget."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIMITS = {
    ".html": 150 * 1024,
    ".css": 100 * 1024,
    ".js": 100 * 1024,
    ".png": 600 * 1024,
    ".jpg": 600 * 1024,
    ".jpeg": 600 * 1024,
    ".webp": 600 * 1024,
    ".svg": 600 * 1024,
}
SKIP_PARTS = {".git", ".worktrees"}


def files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts)
        and path.suffix.lower() in LIMITS
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="keep the command name explicit")
    parser.parse_args()
    failures = []
    for path in files():
        limit = LIMITS[path.suffix.lower()]
        size = path.stat().st_size
        if size > limit:
            failures.append((path.relative_to(ROOT), size, limit))
    if failures:
        for path, size, limit in failures:
            print(f"{path}: {size} bytes exceeds {limit} bytes")
        return 1
    print(f"Performance budget passed for {len(files())} checked assets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
