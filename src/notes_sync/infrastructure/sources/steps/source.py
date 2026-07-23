from datetime import date
from pathlib import Path
from typing import Any

from notes_sync.core.protocols import DiarySource


class StepsSource(DiarySource):
    def __init__(self, steps_file: Path):
        self.steps_file = steps_file

    def _do_fetch(self, start_date: date, end_date: date) -> list[Any]:
        """Reads steps data from a pure text file.
        Format expected:
        2025-12-29,288
        2025-12-30,181
        2025-12-31,5003
        2026-01-01,4665
        2026-01-02,4934
        2026-01-03,461
        2026-01-04,363
        2026-01-05,4098
        """
        if not self.steps_file.exists():
            return []

        try:
            lines = self.steps_file.read_text().splitlines()
            entries = []

            for line in lines:
                parts = line.strip().split(",")
                if len(parts) == 2:
                    date_str, steps_str = parts
                    try:
                        step_val = int(steps_str)
                        entries.append({"date": date_str, "steps": step_val})
                    except ValueError:
                        continue

            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            result = []
            for entry in entries:
                entry_date = entry.get("date")
                if not entry_date or type(entry_date) is not str:
                    continue
                if start_str <= entry_date <= end_str:
                    result.append(entry)

            return result

        except Exception:
            return []
