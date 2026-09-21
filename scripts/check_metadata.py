#!/usr/bin/env python3
"""Check canonical Open Graph/Twitter metadata on static HTML pages."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".worktrees"}
REQUIRED = (
    'property="og:title"',
    'property="og:description"',
    'property="og:url"',
    'property="og:image"',
    'name="twitter:card"',
)
ERROR_PAGES = {"404.html"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="keep the command name explicit")
    parser.parse_args()
    failures: list[str] = []
    pages = 0
    for path in ROOT.rglob("*.html"):
        if any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        pages += 1
        html = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path in ERROR_PAGES:
            pages -= 1
            continue
        missing = [needle for needle in REQUIRED if needle not in html]
        if missing:
            failures.append(f"{path.relative_to(ROOT)}: missing {', '.join(missing)}")
        if 'property="og:url" content="https://divd.works/' not in html:
            failures.append(f"{path.relative_to(ROOT)}: og:url is not canonical")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"Metadata check passed for {pages} HTML pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
