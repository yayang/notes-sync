from datetime import date, datetime
from tempfile import TemporaryDirectory

from notes_sync.infrastructure.sink.obsidian.mapping import DiaryKey, SectionKey
from notes_sync.infrastructure.sink.obsidian.sink import ObsidianSink
from notes_sync.infrastructure.sink.obsidian.sink_trans import ObsidianDiaryTrans
from notes_sync.models.models import (
    CategoryReport,
    Diary,
    DiaryReport,
    DiarySyncContext,
    SleepReport,
    SleepStatus,
    WeatherReport,
    WeatherStatus,
)
from notes_sync.models.schema import SinkName, SyncAction, SyncDecision


class TestObsidianDiaryTrans:
    def test_transform_contains_markers(self):
        trans = ObsidianDiaryTrans()
        diary = Diary(date=datetime(2026, 1, 1))

        content = trans.transform(diary, SyncDecision())

        assert SectionKey.USER_RECORD in content
        assert SectionKey.STATISTICS in content
        assert SectionKey.TIME_ENTRIES in content

    def test_transform_with_steps_override(self):
        """Verify context.steps takes precedence if larger."""
        trans = ObsidianDiaryTrans()
        diary = Diary(
            date=datetime(2026, 1, 1),
            report=DiaryReport(steps=1000),
        )
        # Context says steps should be 2000
        diary.sync_contexts[SinkName.OBSIDIAN] = DiarySyncContext(steps=2000)

        content = trans.transform(
            diary,
            SyncDecision(action=SyncAction.UPDATE, skip_fields={DiaryKey.STEPS.value}),
        )
        assert DiaryKey.STEPS.value not in content

    def test_transform_with_weather(self):
        trans = ObsidianDiaryTrans()
        diary = Diary(
            date=datetime(2026, 1, 1),
            report=DiaryReport(
                weather=WeatherReport(
                    temp_high=25,
                    temp_low=15,
                    weather=WeatherStatus.SUNNY,
                    air_quality=50,
                )
            ),
        )
        content = trans.transform(diary, SyncDecision())

        # Check YAML content
        assert f"{DiaryKey.TEMP_HIGH.value}: 25" in content
        assert f"{DiaryKey.TEMP_LOW.value}: 15" in content
        assert f"{DiaryKey.WEATHER.value}: Sunny" in content

    def test_transform_full_yaml_content(self):
        """Verify all keys are present in YAML."""
        trans = ObsidianDiaryTrans()
        diary = Diary(
            date=datetime(2026, 1, 1),
            report=DiaryReport(
                time={
                    "Focus": CategoryReport(total_seconds=3600),
                    "Play": CategoryReport(total_seconds=7200),
                    "Routine": CategoryReport(total_seconds=1800),
                },
                sleep=SleepReport(
                    bed_time="23:00",
                    bed_status=SleepStatus.ON_TIME,
                    wake_time="07:00",
                    wake_status=SleepStatus.ON_TIME,
                    linger_time="10",
                ),
                weather=WeatherReport(
                    temp_high=30,
                    temp_low=20,
                    weather=WeatherStatus.SUNNY,
                    air_quality=50,
                    pm25=10,
                ),
            ),
        )
        content = trans.transform(diary, SyncDecision())

        assert f"{DiaryKey.FOCUS_HOURS.value}: 1.0" in content
        assert f"{DiaryKey.PLAY_HOURS.value}: 2.0" in content
        assert f"{DiaryKey.ROUTINE_HOURS.value}: 0.5" in content
        # Yaml might quote the time string
        assert f"{DiaryKey.BED_TIME_PREV.value}:" in content
        assert "23:00" in content
        assert f"{DiaryKey.BED_STATUS_PREV.value}: on_time" in content
        assert f"{DiaryKey.LINGER_MINUTES.value}:" in content
        assert "10" in content
        assert f"{DiaryKey.PM25.value}: 10" in content


class TestObsidianSink:
    def test_create_new_file(self):
        with TemporaryDirectory() as tmpdir:
            sink = ObsidianSink(tmpdir)
            today = date(2026, 1, 1)

            formatted_data = {today: "---\ndate: 2026-01-01\n---\nContent"}

            # sink_data(diary_date, data, context, sync_decision)
            context = DiarySyncContext()
            decision = SyncDecision(action=SyncAction.CREATE)
            sink.sink_data(today, formatted_data[today], context, decision)

            # Verify file was created
            file_path = sink.path_resolver.get_diary_path(today)
            assert file_path.exists()
            assert "date: 2026-01-01" in file_path.read_text()

    def test_update_preserves_user_section(self):
        with TemporaryDirectory() as tmpdir:
            sink = ObsidianSink(tmpdir)
            today = date(2026, 1, 1)

            # Create existing file with user content
            file_path = sink.path_resolver.get_diary_path(today)
            file_path.parent.mkdir(parents=True)
            existing_content = f"""---
date: 2026-01-01
---
# 2026-01-01 星期四

{SectionKey.USER_RECORD}
- 用户手写内容保留

{SectionKey.STATISTICS}
旧的统计数据

{SectionKey.TIME_ENTRIES}
旧的时间条目
"""
            file_path.write_text(existing_content, encoding="utf-8")

            # Update with new data
            new_content = f"""---
date: 2026-01-01
steps: 10000
---
# 2026-01-01 星期四

{SectionKey.USER_RECORD}

{SectionKey.STATISTICS}
新的统计数据

{SectionKey.TIME_ENTRIES}
新的时间条目
"""
            # sink_data will see the file exists and update it, preserving user content
            context = DiarySyncContext()
            decision = SyncDecision(action=SyncAction.UPDATE)
            sink.sink_data(today, new_content, context, decision)

            # Verify user section preserved, data sections replaced
            updated = file_path.read_text()
            assert "用户手写内容保留" in updated  # User content preserved
            assert "新的统计数据" in updated  # New stats
            assert "旧的统计数据" not in updated  # Old stats replaced

    def test_update_preserves_body_without_user_record_marker(self):
        with TemporaryDirectory() as tmpdir:
            sink = ObsidianSink(tmpdir)
            today = date(2026, 1, 1)

            file_path = sink.path_resolver.get_diary_path(today)
            file_path.parent.mkdir(parents=True)
            existing_content = f"""---
date: 2026-01-01
---
# 2026-01-01 星期四

这是一段自由正文.

{SectionKey.STATISTICS}
旧的统计数据

{SectionKey.TIME_ENTRIES}
旧的时间条目
"""
            file_path.write_text(existing_content, encoding="utf-8")

            new_content = f"""---
date: 2026-01-01
steps: 10000
---
# 2026-01-01 星期四

{SectionKey.USER_RECORD}

{SectionKey.STATISTICS}
新的统计数据

{SectionKey.TIME_ENTRIES}
新的时间条目
"""
            sink.sink_data(
                today,
                new_content,
                DiarySyncContext(),
                SyncDecision(action=SyncAction.UPDATE),
            )

            updated = file_path.read_text(encoding="utf-8")
            assert "# 2026-01-01 星期四" in updated
            assert "这是一段自由正文." in updated
            assert "新的统计数据" in updated
            assert "旧的统计数据" not in updated

    def test_update_skips_when_existing_body_is_empty(self):
        with TemporaryDirectory() as tmpdir:
            sink = ObsidianSink(tmpdir)
            today = date(2026, 1, 1)

            file_path = sink.path_resolver.get_diary_path(today)
            file_path.parent.mkdir(parents=True)
            existing_content = """---
date: 2026-01-01
---
"""
            file_path.write_text(existing_content, encoding="utf-8")

            new_content = f"""---
date: 2026-01-01
steps: 10000
---
# 2026-01-01 星期四

{SectionKey.USER_RECORD}

{SectionKey.STATISTICS}
新的统计数据

{SectionKey.TIME_ENTRIES}
新的时间条目
"""
            sink.sink_data(
                today,
                new_content,
                DiarySyncContext(),
                SyncDecision(action=SyncAction.UPDATE),
            )

            updated = file_path.read_text(encoding="utf-8")
            assert updated == existing_content
            assert "新的统计数据" not in updated
