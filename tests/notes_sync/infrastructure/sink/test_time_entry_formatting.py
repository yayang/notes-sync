from datetime import date, datetime

import pytest

from notes_sync.infrastructure.sink.notion.mapping import DiaryKey
from notes_sync.infrastructure.sink.notion.sink_trans import NotionDiaryTrans
from notes_sync.infrastructure.sink.obsidian.sink_trans import ObsidianDiaryTrans
from notes_sync.infrastructure.sources.toggl.source_trans import TogglSourceTransformer
from notes_sync.models.models import Diary, TimeEntry
from notes_sync.models.schema import SyncDecision


@pytest.fixture(params=[ObsidianDiaryTrans, NotionDiaryTrans])
def render_entries(request):
    transformer = request.param()

    def render(diary):
        result = transformer.transform(diary, SyncDecision())
        return result if isinstance(result, str) else result[DiaryKey.TIME_ENTRIES]

    return render


def test_overnight_sleep_displays_day_end_without_changing_duration(render_entries):
    start = datetime(2026, 10, 11, 21).astimezone()
    end = datetime(2026, 10, 12, 7).astimezone()
    diaries = TogglSourceTransformer().to_internal_model(
        [
            {
                "start": start.isoformat(),
                "stop": end.isoformat(),
                "duration": 36000,
                "description": "睡觉",
            }
        ]
    )
    evening = diaries[date(2026, 10, 11)]
    morning = diaries[date(2026, 10, 12)]
    before = {day: diary.model_dump() for day, diary in diaries.items()}

    assert "21:00-23:59: 睡觉" in render_entries(evening)
    assert "00:00-07:00: 睡觉" in render_entries(morning)
    assert evening.time_entries[0].duration == 10800
    assert morning.time_entries[0].duration == 25200
    assert {day: diary.model_dump() for day, diary in diaries.items()} == before


@pytest.mark.parametrize(
    "start, end, expected",
    [
        (datetime(2026, 10, 11, 21), datetime(2026, 10, 11, 22), "21:00-22:00"),
        (datetime(2026, 10, 11), datetime(2026, 10, 11), "00:00-00:00"),
        (datetime(2026, 10, 11), datetime(2026, 10, 12), "00:00-23:59"),
        (datetime(2026, 10, 11, 21), datetime(2026, 10, 12, 0, 1), "21:00-00:01"),
    ],
)
def test_only_next_day_midnight_end_is_formatted_as_day_end(
    render_entries, start, end, expected
):
    entry = TimeEntry(
        start=start,
        end=end,
        duration=int((end - start).total_seconds()),
        content="活动",
    )
    diary = Diary(date=start, time_entries=[entry])

    assert f"{expected}: 活动" in render_entries(diary)
