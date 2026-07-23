from datetime import date

from notes_sync.infrastructure.sink.notion.mapping import DiaryKey
from notes_sync.infrastructure.sink.notion.sync_context_trans import (
    NotionSyncContextTrans,
)


def test_notion_context_trans():
    trans = NotionSyncContextTrans()
    raw_data = [
        # Full data with page id (title with date mention)
        {
            "id": "page_id_123",
            "properties": {
                DiaryKey.NAME: {
                    "title": [
                        {
                            "type": "mention",
                            "mention": {
                                "type": "date",
                                "date": {"start": "2026-01-01"},
                            },
                        }
                    ]
                },
                DiaryKey.STATUS: {"select": {"name": "archived"}},
                DiaryKey.STEPS: {"number": 5000},
            },
        },
        # Partial data (no status/steps)
        {
            "id": "page_id_456",
            "properties": {
                DiaryKey.NAME: {
                    "title": [
                        {
                            "type": "mention",
                            "mention": {
                                "type": "date",
                                "date": {"start": "2026-01-02"},
                            },
                        }
                    ]
                },
            },
        },
        # Invalid date
        {
            "id": "page_id_789",
            "properties": {
                DiaryKey.NAME: {
                    "title": [
                        {
                            "type": "mention",
                            "mention": {
                                "type": "date",
                                "date": {"start": "invalid-date"},
                            },
                        }
                    ]
                },
            },
        },
        # Missing date
        {
            "id": "page_id_000",
            "properties": {
                DiaryKey.STATUS: {"select": {"name": "Active"}},
            },
        },
    ]

    context = trans.to_context(raw_data)

    # Verify first entry
    assert date(2026, 1, 1) in context
    assert context[date(2026, 1, 1)].remote_id == "page_id_123"
    assert context[date(2026, 1, 1)].status == "archived"
    assert context[date(2026, 1, 1)].steps == 5000

    # Verify second entry
    assert date(2026, 1, 2) in context
    assert context[date(2026, 1, 2)].remote_id == "page_id_456"
    assert context[date(2026, 1, 2)].status is None
    assert context[date(2026, 1, 2)].steps is None

    # Invalid and missing dates should be skipped
    assert len(context) == 2
