#!/usr/bin/env python3
"""Patch missing Obsidian frontmatter `steps` from a local steps file."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from notes_sync.config.settings import get_settings
from notes_sync.infrastructure.sink.obsidian.mapping import DiaryKey
from notes_sync.infrastructure.sink.obsidian.path_resolver import ObsidianPathResolver

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Patch missing Obsidian frontmatter steps from a steps file."
    )
    parser.add_argument(
        "steps_file",
        type=Path,
        help="Input steps file path.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write changes. Default is dry-run.",
    )
    return parser.parse_args()


def _load_steps(path: Path) -> dict[date, int]:
    if not path.exists():
        raise FileNotFoundError(f"Steps file not found: {path}")

    mapping: dict[date, int] = {}
    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        parts = raw_line.split(",")
        if len(parts) != 2:
            raise ValueError(f"Invalid format at line {lineno}: {raw_line}")
        day = date.fromisoformat(parts[0])
        steps = int(parts[1])
        if day in mapping:
            raise ValueError(f"Duplicate date at line {lineno}: {day.isoformat()}")
        mapping[day] = steps
    if not mapping:
        raise ValueError("Steps file is empty.")
    return mapping


def _find_frontmatter_end(lines: list[str]) -> int | None:
    if not lines or lines[0].strip() != "---":
        return None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return idx
    return None


def _patch_frontmatter(content: str, steps: int) -> tuple[str | None, str]:
    lines = content.splitlines(keepends=True)
    end_idx = _find_frontmatter_end(lines)
    if end_idx is None:
        return None, "missing frontmatter"

    frontmatter = lines[1:end_idx]
    steps_key = f"{DiaryKey.STEPS.value}:"
    if any(line.lstrip().startswith(steps_key) for line in frontmatter):
        return None, "steps already exists"

    insert_idx = end_idx
    linger_key = f"{DiaryKey.LINGER_MINUTES.value}:"
    for idx, line in enumerate(frontmatter, start=1):
        if line.lstrip().startswith(linger_key):
            insert_idx = idx + 1
            break

    lines.insert(insert_idx, f"{DiaryKey.STEPS.value}: {steps}\n")
    return "".join(lines), "patched"


def main() -> int:
    args = _parse_args()
    steps_mapping = _load_steps(args.steps_file)
    resolver = ObsidianPathResolver(str(get_settings().OBSIDIAN_VAULT_PATH))

    patched_count = 0
    skipped_count = 0

    for day in sorted(steps_mapping):
        file_path = resolver.get_diary_path(day)
        if not file_path.exists():
            print(f"skip {day.isoformat()}: file not found -> {file_path}")
            skipped_count += 1
            continue

        original = file_path.read_text(encoding="utf-8")
        updated, reason = _patch_frontmatter(original, steps_mapping[day])
        if updated is None:
            print(f"skip {day.isoformat()}: {reason}")
            skipped_count += 1
            continue

        print(f"patch {day.isoformat()}: steps={steps_mapping[day]} -> {file_path}")
        patched_count += 1
        if args.apply:
            file_path.write_text(updated, encoding="utf-8")

    mode = "apply" if args.apply else "dry-run"
    print(f"{mode} summary: patched={patched_count}, skipped={skipped_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
