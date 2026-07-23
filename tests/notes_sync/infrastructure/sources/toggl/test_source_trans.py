from datetime import date

from notes_sync.infrastructure.sources.toggl.source_trans import (
    TogglSourceTransformer,
)


def test_toggl_transformer_aggregation():
    transformer = TogglSourceTransformer()
    raw_data = [
        {
            "start": "2025-12-15T10:00:00Z",
            "stop": "2025-12-15T12:00:00Z",
            "duration": 7200,
            "description": "Work Task 1",
            "client_name": "Work",
            "project_name": "Development",
            "tags": ["Work"],
        },
        {
            "start": "2025-12-15T14:00:00Z",
            "stop": "2025-12-15T15:00:00Z",
            "duration": 3600,
            "description": "Work Task 2",
            "client_name": "Work",
            "project_name": "Job",
            "tags": ["Work"],
        },
        {
            "start": "2025-12-16T08:00:00Z",
            "stop": "2025-12-16T09:00:00Z",
            "duration": 3600,
            "description": "New Year Task",
            "tags": ["Life"],
        },
    ]

    result = transformer.to_internal_model(raw_data)

    assert len(result) == 2
    assert date(2025, 12, 15) in result
    assert date(2025, 12, 16) in result

    # Check 2025-12-15 entries
    day1 = result[date(2025, 12, 15)]
    assert len(day1.time_entries) == 2
    assert day1.time_entries[0].duration == 7200
    assert day1.time_entries[1].content == "Work Task 2"
    assert day1.time_entries[1].category == "Work"
    assert day1.time_entries[1].sub_category == "Job"
