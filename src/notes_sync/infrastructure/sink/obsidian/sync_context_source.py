"""
Obsidian Meta Source - Reads existing diary files for sync decisions.

IMPORTANT: Obsidian uses file paths as the Sink-side identity (remote_id).
- If file exists: remote_id = str(file_path)
- If file doesn't exist: remote_id = None

This differs from Notion where remote_id is a page UUID.
The same remote_id != None check in Sink determines CREATE vs UPDATE.
"""

from datetime import date, timedelta
from typing import Any

from notes_sync.core.protocols import DiarySyncContextSource
from notes_sync.infrastructure.sink.obsidian.path_resolver import ObsidianPathResolver


class ObsidianSyncContextSource(DiarySyncContextSource):
    """Fetches raw diary file data from Obsidian vault."""

    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.path_resolver = ObsidianPathResolver(vault_path)

    def _do_fetch(self, start_date: date, end_date: date) -> list[Any]:
        """
        Fetch raw file data for date range.

        Returns list of dicts containing:
        - date: the diary date
        - file_path: str path if file exists, None if not
        - content: file content if exists, None if not
        """
        results = []
        days_count = (end_date - start_date).days + 1

        for i in range(days_count):
            cur_date = start_date + timedelta(days=i)
            file_path = self.path_resolver.get_diary_path(cur_date)

            if file_path.exists():
                results.append(
                    {
                        "date": cur_date,
                        "file_path": str(file_path),
                        "content": file_path.read_text(encoding="utf-8"),
                    }
                )
            else:
                results.append(
                    {
                        "date": cur_date,
                        "file_path": None,
                        "content": None,
                    }
                )

        return results
