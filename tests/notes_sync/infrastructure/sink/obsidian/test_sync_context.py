from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from notes_sync.infrastructure.sink.obsidian.path_resolver import ObsidianPathResolver
from notes_sync.infrastructure.sink.obsidian.sync_context_source import (
    ObsidianSyncContextSource,
)
from notes_sync.infrastructure.sink.obsidian.sync_context_trans import (
    ObsidianSyncContextTrans,
)


class TestObsidianPathResolver:
    def test_get_diary_path(self):
        resolver = ObsidianPathResolver("/vault")
        path = resolver.get_diary_path(date(2026, 1, 15))

        expected = Path("/vault/70_Journal/2026/01/2026-01-15.md")
        assert path == expected


class TestObsidianSyncContextSource:
    def test_fetch_raw_data_existing_file(self):
        with TemporaryDirectory() as tmpdir:
            # Create diary file structure
            file_path = Path(tmpdir) / "70_Journal/2026/01/2026-01-01.md"
            file_path.parent.mkdir(parents=True)
            file_path.write_text("---\nstatus: Active\n---\nContent", encoding="utf-8")

            source = ObsidianSyncContextSource(tmpdir)
            result = source.fetch_raw_data(date(2026, 1, 1), date(2026, 1, 1))

            assert len(result) == 1
            assert result[0]["date"] == date(2026, 1, 1)
            assert result[0]["file_path"] == str(file_path)
            assert "status: Active" in result[0]["content"]

    def test_fetch_raw_data_missing_file(self):
        with TemporaryDirectory() as tmpdir:
            source = ObsidianSyncContextSource(tmpdir)
            result = source.fetch_raw_data(date(2099, 1, 1), date(2099, 1, 1))

            assert len(result) == 1
            assert result[0]["date"] == date(2099, 1, 1)
            assert result[0]["file_path"] is None
            assert result[0]["content"] is None


class TestObsidianSyncContextTrans:
    def test_to_context_existing_file(self):
        trans = ObsidianSyncContextTrans()
        raw_data = [
            {
                "date": date(2026, 1, 1),
                "file_path": "/vault/diary.md",
                "content": "---\nstatus: Active\nsteps: 5000\n---\nContent",
            }
        ]

        result = trans.to_context(raw_data)

        assert date(2026, 1, 1) in result
        context = result[date(2026, 1, 1)]
        assert context.remote_id == "/vault/diary.md"
        assert context.status == "Active"
        assert context.steps == 5000

    def test_to_context_missing_file(self):
        trans = ObsidianSyncContextTrans()
        raw_data = [
            {
                "date": date(2026, 1, 1),
                "file_path": None,
                "content": None,
            }
        ]

        result = trans.to_context(raw_data)

        assert date(2026, 1, 1) in result
        context = result[date(2026, 1, 1)]
        assert context.remote_id is None  # No file -> CREATE
