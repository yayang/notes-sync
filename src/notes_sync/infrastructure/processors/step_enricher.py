from datetime import date, datetime

from notes_sync.core.protocols import DiaryEnricher, DiarySource
from notes_sync.models.models import Diary


class StepsEnricher(DiaryEnricher):
    def __init__(self, source: DiarySource):
        self.source = source

    def enrich(self, mapping: dict[date, Diary], start: date, end: date) -> None:
        # Convert date to datetime for protocol compatibility
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())

        # Delegate I/O to source
        entries = self.source.fetch_raw_data(start_dt, end_dt)

        for entry in entries:
            date_str = entry.get("date")
            steps_val = entry.get("steps", 0)
            if not date_str:
                continue

            cur_date = date.fromisoformat(date_str)
            if cur_date in mapping:
                diary = mapping[cur_date]

                diary.report.steps = steps_val
