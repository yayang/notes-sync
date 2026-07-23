#!/usr/bin/env python3
"""Patch Notion `Steps` for a historical range from a local steps file."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from notes_sync.config.settings import get_settings
from notes_sync.infrastructure.sink.notion.mapping import DiaryKey
from notes_sync.infrastructure.sink.notion.sink import NotionSink
from notes_sync.infrastructure.sink.notion.sync_context_source import (
    NotionSyncContextSource,
)
from notes_sync.infrastructure.sink.notion.sync_context_trans import (
    NotionSyncContextTrans,
)
from notes_sync.models.models import DiarySyncContext
from notes_sync.models.schema import SyncAction, SyncDecision


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Patch Notion Steps from a YYYY-MM-DD,steps file."
    )
    parser.add_argument("steps_file", type=Path, help="Input steps file path.")
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write to Notion. Default is dry-run.",
    )
    return parser.parse_args()


def _load_steps(path: Path) -> dict[date, int]:
    if not path.exists():
        raise FileNotFoundError(f"Steps file not found: {path}")

    mapping: dict[date, int] = {}
    for lineno, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split(",")
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


def _slice_steps(
    mapping: dict[date, int],
    start_date: date | None,
    end_date: date | None,
) -> dict[date, int]:
    if start_date is None:
        start_date = min(mapping)
    if end_date is None:
        end_date = max(mapping)
    if start_date > end_date:
        raise ValueError("start_date cannot be later than end_date.")

    return {
        day: steps
        for day, steps in mapping.items()
        if start_date <= day <= end_date
    }


def _fetch_notion_context(start_date: date, end_date: date) -> dict[date, DiarySyncContext]:
    settings = get_settings()
    raw_data = NotionSyncContextSource(
        token=settings.NOTION_TOKEN,
        database_id=settings.NOTION_DATABASE_ID,
    ).fetch_raw_data(start_date, end_date)
    return NotionSyncContextTrans().to_context(raw_data)


def _print_plan(
    target_steps: dict[date, int],
    notion_contexts: dict[date, DiarySyncContext],
) -> tuple[list[tuple[date, str]], list[tuple[date, int, int | None, str]]]:
    missing: list[tuple[date, str]] = []
    updates: list[tuple[date, int, int | None, str]] = []

    for day in sorted(target_steps):
        target = target_steps[day]
        context = notion_contexts.get(day)
        if context is None or context.remote_id is None:
            missing.append((day, "not found in Notion"))
            continue
        if context.steps == target:
            continue
        updates.append((day, target, context.steps, context.remote_id))

    print(f"target_dates={len(target_steps)}")
    print(f"updates={len(updates)}")
    print(f"missing={len(missing)}")

    if updates:
        print("update plan:")
        for day, target, current, _remote_id in updates:
            print(f"  {day.isoformat()}: {current} -> {target}")

    if missing:
        print("missing dates:")
        for day, reason in missing:
            print(f"  {day.isoformat()}: {reason}")

    return missing, updates


def _apply_updates(updates: list[tuple[date, int, int | None, str]]) -> None:
    settings = get_settings()
    sink = NotionSink(settings.NOTION_TOKEN, settings.NOTION_DATABASE_ID)
    sync_decision = SyncDecision(action=SyncAction.UPDATE)

    for day, target, _current, remote_id in updates:
        sink.sink_data(
            diary_date=day,
            data={DiaryKey.STEPS: target},
            context=DiarySyncContext(remote_id=remote_id),
            sync_decision=sync_decision,
        )
        print(f"updated {day.isoformat()} -> {target}")


def main() -> int:
    args = _parse_args()
    all_steps = _load_steps(args.steps_file)
    target_steps = _slice_steps(all_steps, args.start_date, args.end_date)
    if not target_steps:
        raise ValueError("No dates left after range filtering.")

    start_date = min(target_steps)
    end_date = max(target_steps)
    print(f"range={start_date.isoformat()}..{end_date.isoformat()}")

    notion_contexts = _fetch_notion_context(start_date, end_date)
    _missing, updates = _print_plan(target_steps, notion_contexts)

    if not args.apply:
        print("dry-run only; pass --apply to write changes.")
        return 0

    _apply_updates(updates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
