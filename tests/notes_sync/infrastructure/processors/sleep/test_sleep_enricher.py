from datetime import date, datetime
from unittest.mock import MagicMock

from notes_sync.infrastructure.processors.sleep.enricher import SleepEnricher
from notes_sync.models.models import Diary, TimeEntry


def local_dt(year, month, day, hour, minute):
    # 模拟本地时间
    return datetime(year, month, day, hour, minute).astimezone()


def test_sleep_enricher_full_cycle_with_linger():
    # Mock dependencies
    mock_source = MagicMock()
    mock_trans = MagicMock()

    # Constructor no longer needs settings injection
    enricher = SleepEnricher(source=mock_source, trans=mock_trans)

    # 准备数据：
    # 昨天 22:30 睡觉，今天 07:00 醒（睡眠结束），07:30 真正起来（起床动作）
    yesterday = date(2026, 1, 1)
    today = date(2026, 1, 2)

    # 状态 1：模拟 Enricher 内部调用 _fetch_prev_diary 时获取昨天的数据
    # enricher.enrich 会调用 source.fetch_raw_data(yesterday, yesterday)
    # 然后用 trans.to_internal_model(raw) 转换成模型
    yesterday_diary = Diary(
        date=datetime(2026, 1, 1),
        time_entries=[
            TimeEntry(
                start=local_dt(2026, 1, 1, 22, 30),
                end=local_dt(2026, 1, 2, 7, 0),
                sub_category="💤 Sleep",
            )
        ],
    )
    mock_source.fetch_raw_data.return_value = [{"raw": "yesterday_data"}]
    mock_trans.to_internal_model.return_value = {yesterday: yesterday_diary}

    today_diary = Diary(
        date=datetime(2026, 1, 2),
        time_entries=[
            # 今日凌晨条目（已经被 split 过的）
            TimeEntry(
                start=local_dt(2026, 1, 2, 0, 0),
                end=local_dt(2026, 1, 2, 7, 0),
                sub_category="💤 Sleep",
            ),
            # 起床动作：07:30 开始
            TimeEntry(
                start=local_dt(2026, 1, 2, 7, 30),
                end=local_dt(2026, 1, 2, 7, 45),
                content="Get up",
            ),
        ],
    )

    mapping = {today: today_diary}
    enricher.enrich(mapping, start=today, end=today)

    p = today_diary.report
    assert p.sleep.wake_time == "07:30"
    assert p.sleep.wake_status == "on_time"
    # 成功识别到昨晚 22:30 入睡
    assert p.sleep.bed_time == "22:30"
    assert p.sleep.bed_status == "on_time"
    # 赖床时间：07:30 - 07:00 = 30 分钟
    assert p.sleep.linger_time == "30"


def test_sleep_enricher_getup_only_no_sleep():
    """只有起床, 没有 sleep"""
    mock_source = MagicMock()
    mock_trans = MagicMock()
    mock_trans.to_internal_model.return_value = {}

    enricher = SleepEnricher(source=mock_source, trans=mock_trans)

    today = date(2026, 1, 2)
    today_diary = Diary(
        date=datetime(2026, 1, 2),
        time_entries=[
            # 只有起床动作，没有之前的睡眠记录
            TimeEntry(
                start=local_dt(2026, 1, 2, 8, 0),
                end=local_dt(2026, 1, 2, 8, 15),
                content="起床",
            )
        ],
    )

    mapping = {today: today_diary}
    enricher.enrich(mapping, start=today, end=today)

    assert today_diary.report.sleep.wake_time == "08:00"
    assert today_diary.report.sleep.bed_time is None
    assert today_diary.report.sleep.bed_status == "bad_sleep"
    assert today_diary.report.sleep.linger_time is None


def test_sleep_enricher_sleep_only_no_getup():
    """没起床, 有 sleep"""
    mock_source = MagicMock()
    mock_trans = MagicMock()
    mock_trans.to_internal_model.return_value = {}

    enricher = SleepEnricher(source=mock_source, trans=mock_trans)

    # 模拟凌晨入睡：今日 01:00 入睡
    # 根据 SleepConfig.latest_sleep_hour (12)，12:00 之前的睡眠会被认为是当日凌晨入睡
    today = date(2026, 1, 2)
    today_diary = Diary(
        date=datetime(2026, 1, 2),
        time_entries=[
            TimeEntry(
                start=local_dt(2026, 1, 2, 1, 0),
                end=local_dt(2026, 1, 2, 7, 0),
                sub_category="💤 Sleep",
            )
        ],
    )

    mapping = {today: today_diary}
    enricher.enrich(mapping, start=today, end=today)

    assert today_diary.report.sleep.bed_time == "01:00"
    assert today_diary.report.sleep.wake_time is None
    assert today_diary.report.sleep.wake_status == "bad_sleep"
    assert today_diary.report.sleep.linger_time is None


def test_sleep_enricher_no_data():
    """没起床, 没 sleep"""
    mock_source = MagicMock()
    mock_trans = MagicMock()
    mock_trans.to_internal_model.return_value = {}

    enricher = SleepEnricher(source=mock_source, trans=mock_trans)

    today = date(2026, 1, 2)
    today_diary = Diary(
        date=datetime(2026, 1, 2),
        time_entries=[],
    )

    mapping = {today: today_diary}
    enricher.enrich(mapping, start=today, end=today)

    assert today_diary.report.sleep.bed_time is None
    assert today_diary.report.sleep.bed_status == "bad_sleep"
    assert today_diary.report.sleep.wake_time is None
    assert today_diary.report.sleep.wake_status == "bad_sleep"
    assert today_diary.report.sleep.linger_time is None
