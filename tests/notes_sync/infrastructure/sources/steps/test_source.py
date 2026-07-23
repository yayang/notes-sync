from datetime import datetime, timezone

from src.notes_sync.infrastructure.sources.steps.source import StepsSource


def test_steps_source_fetch_raw_data(tmp_path):
    # Prepare dummy data
    steps_file = tmp_path / "steps.csv"
    data = """2024-01-01,5000
2024-01-02,8000
2024-01-03,12000"""
    steps_file.write_text(data)

    source = StepsSource(steps_file)

    # Test filtering
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)

    raw_data = source.fetch_raw_data(start, end)

    assert len(raw_data) == 2
    assert raw_data[0]["steps"] == 5000
    assert raw_data[1]["steps"] == 8000


def test_steps_source_file_not_found(tmp_path):
    source = StepsSource(tmp_path / "non_existent.json")
    raw_data = source.fetch_raw_data(datetime.now(), datetime.now())
    assert raw_data == []
