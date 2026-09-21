#!/usr/bin/env python3
"""Audit image alt text in the checked-in HTML."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMAGE_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE | re.DOTALL)
ALT_RE = re.compile(r"\balt\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)
HIDDEN_RE = re.compile(r"\baria-hidden\s*=\s*[\"']true[\"']", re.IGNORECASE)
SKIP_PARTS = {".git", ".worktrees"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="keep the command name explicit")
    parser.parse_args()
    failures: list[str] = []
    count = 0
    for path in ROOT.rglob("*.html"):
        if any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        for tag in IMAGE_RE.findall(path.read_text(encoding="utf-8")):
            count += 1
            match = ALT_RE.search(tag)
            if not match:
                failures.append(f"{path.relative_to(ROOT)}: image is missing alt")
                continue
            if not match.group(2).strip() and not HIDDEN_RE.search(tag):
                failures.append(f"{path.relative_to(ROOT)}: content/linked image has empty alt")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"Alt-text audit passed for {count} images.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
