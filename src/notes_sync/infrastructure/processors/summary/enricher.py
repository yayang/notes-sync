from datetime import date
from typing import Optional

from notes_sync.core.protocols import DiaryEnricher
from notes_sync.infrastructure.processors.summary.mapping import (
    STATISTICS_LABELS,
    CategoryKey,
    LabelKey,
)
from notes_sync.models.models import (
    CategoryReport,
    Diary,
    SleepReport,
)


class SummaryEnricher(DiaryEnricher):
    def enrich(self, mapping: dict[date, Diary], start: date, end: date) -> None:
        """Orchestrator: 仅负责跨日调度。"""
        for diary in mapping.values():
            """Sub-Orchestrator: 描述摘要的构成章节。"""
            p = diary.report

            sections = [
                self._process_statistics(p.time),
                self._process_sleep_info(p.sleep),
                self._process_extension_info(diary.report.steps),
            ]

            p.summary = "\n".join(filter(None, sections))

    def _process_statistics(self, stats: dict) -> Optional[str]:
        if not stats:
            return None
        lines = []
        for key in CategoryKey:
            if usage := stats.get(key):
                lines.append(self.__build_statistic_line(key, usage))
        return "\n".join(lines)

    def _process_sleep_info(self, stats: SleepReport) -> Optional[str]:
        lines = []
        # 显示入睡信息（即使时间为空，但有状态）
        if stats.bed_time or stats.bed_status:
            time_str = stats.bed_time or "N/A"
            status = stats.bed_status.value if stats.bed_status else "N/A"
            lines.append(f"{LabelKey.BED_TIME_PREV}({time_str}): {status}")
        # 显示起床信息（即使时间为空，但有状态）
        if stats.wake_time or stats.wake_status:
            time_str = stats.wake_time or "N/A"
            status = stats.wake_status.value if stats.wake_status else "N/A"
            lines.append(f"{LabelKey.UP_TIME}({time_str}): {status}")

        # 赖床信息
        if stats.linger_time:
            lines.append(f"{LabelKey.LINGER_MINUTES}: {stats.linger_time} min")
        return "\n".join(lines) if lines else None

    def _process_extension_info(self, steps: Optional[int]) -> Optional[str]:
        if steps is not None:
            steps_fmt = "{:,}".format(steps)  # 用,对数字添加千位分隔
            return f"{LabelKey.STEPS}: {steps_fmt} steps"
        return None

    def __build_statistic_line(self, key: CategoryKey, usage: CategoryReport) -> str:
        """
        原子工具: 仅负责小时转换与 Breakdown 拼接。

        Example:
            Input: key=CategoryKey.FOCUS, usage={total_seconds: 7200, breakdown={"写作": 5400, "阅读": 1800}}
            Output: "🌱 成长(2.0h): 写作(1.5h), 阅读(0.5h)"
        """
        total_h = round(usage.total_seconds / 3600, 2)
        display = STATISTICS_LABELS.get(key) or key.value

        detail = self.__format_breakdown(usage.breakdown) if usage.breakdown else ""
        return f"{display}({total_h}h){detail}"

    def __format_breakdown(self, breakdown: dict) -> str:
        """
        原子工具: 专门负责排序和生成后缀字符串。

        Example:
            Input: {"写作": 5400, "阅读": 1800}
            Output: ": 写作(1.5h), 阅读(0.5h)"
        """
        sorted_items = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
        parts = [f"{name}({round(sec / 3600, 1)}h)" for name, sec in sorted_items]
        return ": " + ", ".join(parts)
