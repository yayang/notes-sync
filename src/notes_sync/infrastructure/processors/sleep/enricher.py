from datetime import date, datetime, timedelta
from typing import Optional

from notes_sync.core.protocols import DiaryEnricher, DiarySource, DiarySourceTransformer
from notes_sync.infrastructure.processors.sleep.config import SleepConfig
from notes_sync.models.models import Diary, SleepStatus, TimeEntry


class SleepEnricher(DiaryEnricher):
    def __init__(
        self,
        source: DiarySource,
        trans: DiarySourceTransformer,
    ):
        self.source = source
        self.trans = trans
        self.settings = SleepConfig()

    def enrich(self, mapping: dict[date, Diary], start: date, end: date) -> None:
        """识别并分析睡眠数据（入睡/起床时间及状态检测）"""
        # 显式获取 start 前一天的上下文
        prev_diary = self._fetch_prev_diary(mapping, start)

        days_count = (end - start).days + 1

        for i in range(days_count):
            cur_date = start + timedelta(days=i)
            diary = mapping.get(cur_date)

            if not diary:  # 断档：重置上下文，因为下一天无法通过它查找昨天
                prev_diary = None
                continue

            getup_entry = self.__find_getup_entry(diary.time_entries)

            self._process_sleep(diary, prev_diary)
            if getup_entry:
                self._process_getup(diary, getup_entry)
                self._process_linger(diary, getup_entry)
            else:
                # 没起床：状态设为 BAD_SLEEP
                diary.report.sleep.wake_status = SleepStatus.BAD_SLEEP

            prev_diary = diary

    def _process_sleep(self, diary: Diary, prev_diary: Optional[Diary]):
        sleep_entry, is_yd = self.__find_sleep_entry(diary.time_entries, prev_diary)

        # 设置入睡时间和状态
        if sleep_entry:
            self.__apply_gotobed(diary, sleep_entry.start, is_yd)
        else:
            # 没入睡：状态设为 BAD_SLEEP
            diary.report.sleep.bed_status = SleepStatus.BAD_SLEEP

    def _process_getup(self, diary: Diary, getup_entry: TimeEntry):
        self.__apply_getup(diary, getup_entry.start)

    def _process_linger(self, diary: Diary, getup_entry: TimeEntry):
        sleep_before_getup_entry = self.__find_linger(diary, getup_entry.start)
        if sleep_before_getup_entry:
            self.__apply_linger(diary, sleep_before_getup_entry.end, getup_entry.start)

    def _fetch_prev_diary(
        self, mapping: dict[date, Diary], start: date
    ) -> Optional[Diary]:
        prev_date = start - timedelta(days=1)

        raw = self.source.fetch_raw_data(prev_date, prev_date)
        internal = self.trans.to_internal_model(raw)
        return internal.get(prev_date)

    def __to_datetime(self, dt_obj: datetime | date) -> datetime:
        """Helper to ensure we're working with a datetime object."""
        if isinstance(dt_obj, date) and not isinstance(dt_obj, datetime):
            return datetime(dt_obj.year, dt_obj.month, dt_obj.day)
        return dt_obj

    def __find_sleep_entry(
        self, current_entries: list[TimeEntry], prev_diary: Optional[Diary]
    ) -> tuple[Optional[TimeEntry], bool]:
        target_sleep_entry = None
        is_yd = False
        settings = self.settings

        """1. 优先查昨天 (需要先对昨天数据排序，如果有的话)"""
        if prev_diary:
            prev_entries = prev_diary.time_entries
            for e in reversed(prev_entries):
                if e.start.hour < settings.earliest_sleep_hour_yd:
                    break
                if e.sub_category == settings.category:
                    target_sleep_entry = e
                    is_yd = True
                    break

        """2. 如果昨天没找到（或太早），找今天第一个（凌晨入睡）"""
        if not target_sleep_entry:
            for e in current_entries:
                if e.start.hour > settings.latest_sleep_hour:
                    break
                if e.sub_category == settings.category:
                    target_sleep_entry = e
                    break

        return target_sleep_entry, is_yd

    def __find_getup_entry(self, entries: list[TimeEntry]) -> Optional[TimeEntry]:
        settings = self.settings
        for e in entries:
            if e.start.hour < settings.earliest_getup_hour or not e.content:
                continue
            if any(e.content.startswith(kw) for kw in settings.getup_keys):
                return e
        return None

    def __parse_time_str(self, time_str: str) -> int:
        """Convert HH:MM string to minutes from midnight."""
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    def __apply_gotobed(self, diary: Diary, start: datetime, is_yd: bool) -> None:
        dt = self.__to_datetime(start)
        sleep = diary.report.sleep
        sleep.bed_time = dt.strftime("%H:%M")
        settings = self.settings

        if is_yd:
            sleep.bed_status = SleepStatus.ON_TIME
        else:
            minutes = dt.hour * 60 + dt.minute

            # Parse Configured Thresholds
            t_on_time = self.__parse_time_str(settings.gotobed_on_time)
            t_late = self.__parse_time_str(settings.gotobed_late)
            t_too_late = self.__parse_time_str(settings.gotobed_too_late)

            if minutes <= t_on_time:
                sleep.bed_status = SleepStatus.ON_TIME
            elif minutes <= t_late:
                sleep.bed_status = SleepStatus.LITTLE_LATE
            elif minutes <= t_too_late:
                sleep.bed_status = SleepStatus.TOO_LATE
            else:
                sleep.bed_status = SleepStatus.BAD_SLEEP

    def __apply_getup(self, diary: Diary, start: datetime) -> None:
        dt = self.__to_datetime(start)
        sleep = diary.report.sleep
        sleep.wake_time = dt.strftime("%H:%M")
        settings = self.settings

        minutes = dt.hour * 60 + dt.minute

        # Parse Configured Thresholds
        t_on_time = self.__parse_time_str(settings.getup_on_time)
        t_late = self.__parse_time_str(settings.getup_late)
        t_too_late = self.__parse_time_str(settings.getup_too_late)

        if minutes < t_on_time:
            sleep.wake_status = SleepStatus.ON_TIME
        elif minutes < t_late:
            sleep.wake_status = SleepStatus.LITTLE_LATE
        elif minutes < t_too_late:
            sleep.wake_status = SleepStatus.TOO_LATE
        else:
            sleep.wake_status = SleepStatus.AFTER_NOON

    def __find_linger(self, diary: Diary, getup_time: datetime) -> Optional[TimeEntry]:
        for e in reversed(diary.time_entries):
            # 必须在起床动作之前，且属于睡眠类
            if e.start < getup_time and e.sub_category == self.settings.category:
                return e
        return None

    def __apply_linger(
        self, diary: Diary, sleep_end: datetime, getup_time: datetime
    ) -> None:
        diff = getup_time - sleep_end
        minutes = int(diff.total_seconds() / 60)
        # Use Configured Threshold
        if 0 <= minutes < self.settings.linger_threshold_max:
            diary.report.sleep.linger_time = str(minutes)
