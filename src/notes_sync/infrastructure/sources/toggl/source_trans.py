from datetime import date, datetime
from typing import Any

from notes_sync.core.protocols import DiarySourceTransformer
from notes_sync.models.models import Diary, TimeEntry


class TogglSourceTransformer(DiarySourceTransformer):
    def to_internal_model(self, raw_data: list[dict[str, Any]]) -> dict[date, Diary]:
        """Aggregates raw Toggl time entries by date. Cross-day entries are split at midnight."""
        diary_map: dict[date, Diary] = {}

        for entry in raw_data:
            # Parse UTC times and convert to local timezone
            start_dt = datetime.fromisoformat(
                entry["start"].replace("Z", "+00:00")
            ).astimezone()
            end_dt = (
                datetime.fromisoformat(
                    entry["stop"].replace("Z", "+00:00")
                ).astimezone()
                if entry.get("stop")
                else start_dt
            )

            base_entry = TimeEntry(
                start=start_dt,
                end=end_dt,
                duration=entry.get("duration", 0),
                content=entry.get("description", "No Description"),
                category=entry.get("client_name", "No Client"),
                sub_category=entry.get("project_name", "No Project"),
                tags=entry.get("tags", []),
            )

            for split_entry in self.__split_overnight(base_entry):
                local_date = split_entry.start.date()
                if local_date not in diary_map:
                    diary_map[local_date] = Diary(
                        date=datetime.combine(local_date, datetime.min.time()),
                        time_entries=[],
                    )
                diary_map[local_date].time_entries.append(split_entry)

        for diary in diary_map.values():
            diary.time_entries.sort(key=lambda x: x.start)

        return diary_map

    def __split_overnight(self, entry: TimeEntry) -> list[TimeEntry]:
        """如果条目跨天，拆成两段；否则原样返回。"""
        start = entry.start
        end = entry.end

        if start.date() == end.date():
            return [entry]

        midnight = datetime.combine(end.date(), datetime.min.time()).astimezone(
            start.tzinfo
        )
        return [
            entry.model_copy(
                update={
                    "end": midnight,
                    "duration": int((midnight - start).total_seconds()),
                }
            ),
            entry.model_copy(
                update={
                    "start": midnight,
                    "duration": int((end - midnight).total_seconds()),
                }
            ),
        ]
