from datetime import date, datetime, timedelta

from notes_sync.infrastructure.processors.statistics.enricher import StatisticsEnricher
from notes_sync.models.models import Diary, TimeEntry


def local_dt(year, month, day, hour, minute):
    # Returns timezone-aware datetime
    return datetime(year, month, day, hour, minute).astimezone()


def test_statistics_enricher_categorization():
    enricher = StatisticsEnricher()

    diary = Diary(
        date=datetime(2026, 1, 5),
        time_entries=[
            # 1. Focus (60 mins)
            TimeEntry(
                start=local_dt(2026, 1, 5, 9, 0),
                end=local_dt(2026, 1, 5, 10, 0),
                duration=3600,
                category="💼 WORK",
                sub_category="💻 Develop",
            ),
            # 2. Target Project (Play) (30 mins)
            TimeEntry(
                start=local_dt(2026, 1, 5, 10, 0),
                end=local_dt(2026, 1, 5, 10, 30),
                duration=1800,
                category="Life",
                sub_category="🍿 被动娱乐",
            ),
            # 3. Target Project (Routine) (30 mins)
            TimeEntry(
                start=local_dt(2026, 1, 5, 11, 0),
                end=local_dt(2026, 1, 5, 11, 30),
                duration=1800,
                category="Life",
                sub_category="🏠 家务通勤",
            ),
            # 4. Others (30 mins)
            TimeEntry(
                start=local_dt(2026, 1, 5, 12, 0),
                end=local_dt(2026, 1, 5, 12, 30),
                duration=1800,
                category="Unknown Client",
                sub_category="Unknown Project",
            ),
        ],
    )

    # Use past date so Unrecorded is calculated fully to end of day logic
    past_date = date(2026, 1, 1)
    diary.date = datetime(2026, 1, 1).astimezone()
    # Adjust entries to match 2026-01-01
    diary.time_entries[0].start = local_dt(2026, 1, 1, 9, 0)
    diary.time_entries[0].end = local_dt(2026, 1, 1, 10, 0)
    diary.time_entries[1].start = local_dt(2026, 1, 1, 10, 0)
    diary.time_entries[1].end = local_dt(2026, 1, 1, 10, 30)
    diary.time_entries[2].start = local_dt(2026, 1, 1, 11, 0)
    diary.time_entries[2].end = local_dt(2026, 1, 1, 11, 30)
    diary.time_entries[3].start = local_dt(2026, 1, 1, 12, 0)
    diary.time_entries[3].end = local_dt(2026, 1, 1, 12, 30)

    mapping = {past_date: diary}
    enricher.enrich(mapping, start=past_date, end=past_date)

    report = diary.report.time

    # Assert Focus breakdown (60 min = 3600 sec)
    assert report["Focus"].total_seconds == 3600
    assert report["Focus"].breakdown["💻 Develop"] == 3600

    # Assert Play (30 min = 1800 sec)
    assert report["Play"].total_seconds == 1800
    assert report["Play"].breakdown["🍿 被动娱乐"] == 1800

    # Assert Routine (30 min = 1800 sec)
    assert report["Routine"].total_seconds == 1800

    # Assert Others (30 min = 1800 sec)
    assert report["Others"].total_seconds == 1800
    assert report["Others"].breakdown["Unknown Project"] == 1800

    # Unrecorded (1290 min = 77400 sec)
    assert report["Unrecorded"].total_seconds == 77400
    # Unrecorded has no breakdown
    assert len(report["Unrecorded"].breakdown) == 0


def test_statistics_enricher_gap_today():
    enricher = StatisticsEnricher()
    now = datetime.now().astimezone()
    today = now.date()

    start_time = datetime.combine(today, datetime.min.time()).astimezone()
    # Use only 1 minute duration to ensure we are likely within "Past" relative to now (unless running exactly at 00:00)
    entry_end = start_time + timedelta(minutes=1)

    diary = Diary(
        date=start_time,
        time_entries=[
            TimeEntry(
                start=start_time,
                end=entry_end,
                duration=60,
                category="Some Category",
                sub_category="Some Project",
            )
        ],
    )

    mapping = {today: diary}
    enricher.enrich(mapping, start=today, end=today)

    report = diary.report.time

    assert report["Others"].total_seconds == 60  # 1 min = 60 sec

    actual_now = datetime.now().astimezone()
    expected_gap_seconds = (actual_now - entry_end).total_seconds()
    expected_gap_seconds = max(expected_gap_seconds, 0)

    actual_unrecorded_seconds = 0
    if "Unrecorded" in report:
        actual_unrecorded_seconds = report["Unrecorded"].total_seconds

    # Allow 60 seconds tolerance (1 minute)
    assert abs(actual_unrecorded_seconds - expected_gap_seconds) <= 60
