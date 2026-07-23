from typing import Any

from notes_sync.core.protocols import DiarySinkTransformer
from notes_sync.infrastructure.sink.notion.mapping import DiaryKey
from notes_sync.models.models import Diary
from notes_sync.models.schema import KVProxy, SyncDecision


class NotionDiaryTrans(DiarySinkTransformer[dict[str, Any]]):
    """Transforms internal Diary model to (remote_id, Notion Properties)."""

    def transform(self, diary: Diary, sync_decision: SyncDecision) -> dict[str, Any]:
        """Build Notion properties dict from Diary, using embedded context."""

        props = KVProxy({}, sync_decision.skip_fields)
        report = diary.report

        # 1. Time Categories
        self.__apply_time_stats(props, report.time)

        # 2. Sleep Report
        self.__apply_sleep_stats(props, report.sleep)

        # 3. Steps
        props[DiaryKey.STEPS] = report.steps

        # 4. Statistics (Summary)
        props[DiaryKey.STATISTICS] = report.summary

        # 5. Time Entries
        props[DiaryKey.TIME_ENTRIES] = self.__format_time_entries(diary.time_entries)

        # 6. Icon
        props[DiaryKey.ICON] = report.icon

        # 7. Weather
        self.__apply_weather_stats(props, report.weather)

        props[DiaryKey.STATUS] = diary.status

        return props.unwrap()

    def __apply_weather_stats(self, props: KVProxy, weather: Any) -> None:
        """Map weather stats to Notion properties."""
        if not weather:
            return
        props[DiaryKey.TEMP_HIGH] = weather.temp_high
        props[DiaryKey.TEMP_LOW] = weather.temp_low
        props[DiaryKey.WEATHER] = weather.weather.value
        props[DiaryKey.AIR_QUALITY] = weather.air_quality
        props[DiaryKey.PM25] = weather.pm25

    def __apply_sleep_stats(self, props: KVProxy, sleep: Any) -> None:
        """Map sleep stats to Notion properties."""
        props[DiaryKey.BED_TIME_PREV] = sleep.bed_time or ""
        if sleep.bed_status:
            props[DiaryKey.BED_STATUS_PREV] = sleep.bed_status.value
        props[DiaryKey.GETUP_TIME] = sleep.wake_time or ""
        if sleep.wake_status:
            props[DiaryKey.GETUP_STATUS] = sleep.wake_status.value
        props[DiaryKey.LINGER_MINUTES] = sleep.linger_time or "0"

    def __format_time_entries(self, entries: list) -> str:
        """Format time entries as readable string (local timezone)."""
        lines = []
        for entry in entries:
            start = entry.start.strftime("%H:%M")
            end = entry.end.strftime("%H:%M")
            content = entry.content or entry.sub_category or "N/A"
            lines.append(f"{start}-{end}: {content}")
        return "\n".join(lines)

    def __apply_time_stats(self, props: KVProxy, time_report: dict[str, Any]) -> None:
        """Map time category stats to Notion properties."""
        # 内部 category key (字符串) -> Notion DiaryKey 映射
        category_map = {
            "Focus": DiaryKey.FOCUS_HOURS,
            "Play": DiaryKey.PLAY_HOURS,
            "Sleep": DiaryKey.SLEEP_HOURS,
            "Routine": DiaryKey.ROUTINE_HOURS,
        }
        for cat_key, diary_key in category_map.items():
            if cat_key in time_report:
                hours = time_report[cat_key].total_seconds / 3600
                props[diary_key] = round(hours, 2)
            else:
                props[diary_key] = 0.0
