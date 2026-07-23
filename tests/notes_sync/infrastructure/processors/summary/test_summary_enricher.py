from datetime import date, datetime

from notes_sync.infrastructure.processors.summary.enricher import SummaryEnricher
from notes_sync.models.models import (
    CategoryReport,
    Diary,
    DiaryReport,
    SleepReport,
)


def test_summary_enricher():
    enricher = SummaryEnricher()
    today = date(2026, 1, 5)

    # Construct time_report (values in seconds)
    u_focus = CategoryReport(
        total_seconds=13860, breakdown={"Creation": 10440, "Reading": 2160}
    )  # 3.85h, 2.9h, 0.6h
    u_sleep = CategoryReport(total_seconds=28800, breakdown={"Deep Sleep": 28800})  # 8h
    # Unrecorded has no breakdown
    u_unrecorded = CategoryReport(total_seconds=6480)  # 1.8h

    time_data = {"Focus": u_focus, "Sleep": u_sleep, "Unrecorded": u_unrecorded}

    p = DiaryReport(
        time=time_data,
        sleep=SleepReport(
            bed_time="00:05",
            bed_status="on_time",
            wake_time="08:05",
            wake_status="on_time",
            linger_time="15",
        ),
        steps=4934,
    )

    diary = Diary(date=datetime(2026, 1, 5), time_entries=[], report=p)

    mapping = {today: diary}
    enricher.enrich(mapping, start=today, end=today)

    summary = diary.report.summary

    # Assertions
    # Focus: 231/60 = 3.85.
    # Check Project order (Creation 2.9, Reading 0.6).
    assert "🎯 专注(3.85h): Creation(2.9h), Reading(0.6h)" in summary

    # Sleep: 480/60 = 8.0
    # Deep Sleep (8.0h)
    assert "💤 睡眠(8.0h): Deep Sleep(8.0h)" in summary
    # Unrecorded: 1.8h
    assert "❓ 空白(1.8h)" in summary
    # Sleep info
    assert "🌙 昨晚就寝(00:05): on_time" in summary
    assert "☀️ 今日起床(08:05): on_time" in summary
    assert "🛌 赖床分钟: 15 min" in summary
    # Steps
    assert "🚶 步数: 4,934 steps" in summary


def test_summary_enricher_zero_linger():
    """Verify that linger_time="0" is displayed."""
    enricher = SummaryEnricher()
    today = date(2026, 1, 6)

    p = DiaryReport(
        sleep=SleepReport(
            bed_time="00:00",
            bed_status="on_time",
            wake_time="08:00",
            wake_status="on_time",
            linger_time="0",
        )
    )
    diary = Diary(date=datetime(2026, 1, 6), time_entries=[], report=p)
    mapping = {today: diary}

    enricher.enrich(mapping, start=today, end=today)
    summary = diary.report.summary

    assert "🛌 赖床分钟: 0 min" in summary
