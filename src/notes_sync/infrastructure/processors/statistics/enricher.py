from datetime import date, datetime, timedelta

from notes_sync.core.protocols import DiaryEnricher, EnricherPriority
from notes_sync.infrastructure.processors.statistics.mapping import (
    ACTIVITY_TO_CATEGORY,
    AreaLabel,
    CategoryKey,
)
from notes_sync.models.models import CategoryReport, Diary, TimeEntry


class StatisticsEnricher(DiaryEnricher):
    priority = EnricherPriority.HIGH

    def enrich(self, mapping: dict[date, Diary], start: date, end: date) -> None:
        """统计各分类时长，未匹配的归入 Others，未记录时间归入 Unrecorded。"""
        for cur_date, diary in mapping.items():
            self._process_entries(cur_date, diary)

    def __get_time_boundaries(
        self, cur_date: date, diary: Diary
    ) -> tuple[datetime, datetime]:
        day_start, now = diary.date.astimezone(), datetime.now().astimezone()
        if cur_date == now.date():
            day_end = now
        elif cur_date < now.date():
            day_end = day_start + timedelta(days=1)
        else:
            day_end = day_start
        return day_start, day_end

    def _process_entries(self, cur_date: date, diary: Diary) -> None:
        day_start, day_end = self.__get_time_boundaries(cur_date, diary)

        report = diary.report.time
        total_day_seconds = (day_end - day_start).total_seconds()
        recorded_seconds = 0.0

        for entry in diary.time_entries:
            duration = self.__get_entry_duration(entry)
            recorded_seconds += duration

            cate_key = self.__categorize_entry(entry)
            self.__accumulate_usage(report, cate_key, duration, entry.sub_category)

        # 未记录时间
        unrecorded = max(total_day_seconds - recorded_seconds, 0)
        if unrecorded > 0:
            self.__accumulate_usage(report, CategoryKey.UNRECORDED, unrecorded, None)

    def __accumulate_usage(
        self, report: dict, cate_key: str, duration: float, activity: str | None
    ) -> None:
        """累加分类时长和 breakdown。"""
        if cate_key not in report:
            report[cate_key] = CategoryReport()
        report[cate_key].total_seconds += duration

        if activity:
            report[cate_key].breakdown[activity] = (
                report[cate_key].breakdown.get(activity, 0) + duration
            )

    def __get_entry_duration(self, entry: TimeEntry) -> float:
        duration = entry.duration or (entry.end - entry.start).total_seconds()
        return max(duration, 0)

    def __categorize_entry(self, entry: TimeEntry) -> str:
        # 优先匹配 project (sub_category) 到具体分类
        if cat := self.__get_category_from_sub_category(entry.sub_category):
            return cat
        # 兜底: 根据 client (category) 大致分类
        if entry.category == AreaLabel.LIFE:
            return CategoryKey.PLAY
        if entry.category == AreaLabel.HEALTH:
            return CategoryKey.RECHARGE
        return CategoryKey.OTHERS

    def __get_category_from_sub_category(self, sub_category: str | None) -> str | None:
        if (
            sub_category
            and type(sub_category) is str
            and (cat := ACTIVITY_TO_CATEGORY.get(sub_category))
        ):
            return cat
        return None
