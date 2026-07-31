from datetime import date
from typing import Any

import yaml

from notes_sync.core.protocols import DiarySinkTransformer
from notes_sync.infrastructure.sink.obsidian.mapping import (
    DiaryKey,
    SectionKey,
    UserSection,
)
from notes_sync.models.models import (
    Diary,
    SleepReport,
)
from notes_sync.models.schema import KVProxy, SyncDecision


class ObsidianDiaryTrans(DiarySinkTransformer[str]):
    """Transforms Diary to Obsidian markdown format."""

    def transform(self, diary: Diary, sync_decision: SyncDecision) -> str:
        """Build complete markdown content from Diary, using embedded context."""
        yaml_section = self.__build_yaml(diary, sync_decision)
        header = self.__build_header(diary.date.date())
        statistics = self.__build_statistics(diary)
        time_entries = self.__build_time_entries(diary)

        return (
            f"{yaml_section}\n{header}\n\n{UserSection}\n{statistics}\n{time_entries}"
        )

    def __build_yaml(self, diary: Diary, sync_decision: SyncDecision) -> str:
        """Build YAML frontmatter."""
        report = diary.report

        props = KVProxy(
            {
                DiaryKey.DATE.value: diary.date.date().isoformat(),
                DiaryKey.STATUS.value: diary.status or "current",
            },
            sync_decision.skip_fields,
        )

        # Time stats
        self.__apply_time_stats(props, report.time)

        # Sleep report
        self.__apply_sleep_stats(props, report.sleep)

        # Steps
        props[DiaryKey.STEPS.value] = report.steps

        # Weather
        self.__apply_weather_stats(props, report.weather)

        yaml_str = yaml.dump(props.unwrap(), allow_unicode=True, sort_keys=False)
        return f"---\n{yaml_str}---"

    def __apply_weather_stats(self, data: KVProxy, weather: Any) -> None:
        """Map weather stats to YAML fields."""
        if not weather:
            return
        data[DiaryKey.TEMP_HIGH.value] = weather.temp_high
        data[DiaryKey.TEMP_LOW.value] = weather.temp_low
        data[DiaryKey.WEATHER.value] = weather.weather.value
        data[DiaryKey.AIR_QUALITY.value] = weather.air_quality
        data[DiaryKey.PM25.value] = weather.pm25

    def __apply_sleep_stats(self, data: KVProxy, sleep: SleepReport) -> None:
        """Map sleep stats to YAML fields."""
        data[DiaryKey.BED_TIME_PREV.value] = sleep.bed_time or ""
        if sleep.bed_status:
            data[DiaryKey.BED_STATUS_PREV.value] = sleep.bed_status.value
        data[DiaryKey.GETUP_TIME.value] = sleep.wake_time or ""
        if sleep.wake_status:
            data[DiaryKey.GETUP_STATUS.value] = sleep.wake_status.value
        data[DiaryKey.LINGER_MINUTES.value] = sleep.linger_time or "0"

    def __apply_time_stats(self, data: KVProxy, time_report: dict) -> None:
        """Map time category stats to YAML fields."""
        category_map = {
            "Focus": DiaryKey.FOCUS_HOURS,
            "Play": DiaryKey.PLAY_HOURS,
            "Sleep": DiaryKey.SLEEP_HOURS,
            "Routine": DiaryKey.ROUTINE_HOURS,
            "Unrecorded": DiaryKey.UNRECORDED_HOURS,
        }
        for cat_key, diary_key in category_map.items():
            if cat_key in time_report:
                hours = time_report[cat_key].total_seconds / 3600
                data[diary_key.value] = round(hours, 2)
            else:
                data[diary_key.value] = 0.0

    def __build_statistics(self, diary: Diary) -> str:
        """Build STATISTICS section."""
        summary = diary.report.summary or ""
        return f"{SectionKey.STATISTICS}\n{summary}"

    def __build_time_entries(self, diary: Diary) -> str:
        """Build TIME_ENTRIES section."""
        lines = []
        for entry in diary.time_entries:
            start = entry.start.strftime("%H:%M")
            end = entry.end.strftime("%H:%M")
            content = entry.content or entry.sub_category or "N/A"
            lines.append(f"- {start}-{end}: {content}")

        entries_str = "\n".join(lines) if lines else ""
        return f"{SectionKey.TIME_ENTRIES}\n{entries_str}"

    def __build_header(self, diary_date: date) -> str:
        """Build header with date and Chinese weekday."""
        weekdays = [
            "星期一",
            "星期二",
            "星期三",
            "星期四",
            "星期五",
            "星期六",
            "星期日",
        ]
        weekday = weekdays[diary_date.weekday()]
        return f"# {diary_date.isoformat()} {weekday}"
