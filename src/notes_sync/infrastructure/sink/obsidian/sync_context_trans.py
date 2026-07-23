from datetime import date
from typing import Any

import yaml

from notes_sync.core.protocols import DiarySyncContextTransformer
from notes_sync.infrastructure.sink.obsidian.mapping import DiaryKey
from notes_sync.models.models import DiarySyncContext


class ObsidianSyncContextTrans(DiarySyncContextTransformer):
    """
    Transforms raw Obsidian file data into DiarySyncContext.

    remote_id is set to file_path if file exists, enabling CREATE/UPDATE logic:
    - remote_id is not None → file exists → UPDATE (preserve UserSection)
    - remote_id is None → file doesn't exist → CREATE (write full content)
    """

    def to_context(self, raw_data: list[Any]) -> dict[date, DiarySyncContext]:
        result = {}

        for entry in raw_data:
            cur_date = entry.get("date")
            if not cur_date:
                continue

            file_path = entry.get("file_path")
            content = entry.get("content")

            # Parse YAML frontmatter if file exists
            yaml_data = self.__extract_yaml(content) if content else {}

            result[cur_date] = DiarySyncContext(
                remote_id=file_path,  # file path as Sink-side identity
                status=yaml_data.get(DiaryKey.STATUS),
                steps=yaml_data.get(DiaryKey.STEPS),
            )

        return result

    def __extract_yaml(self, content: str) -> dict:
        """Extract YAML frontmatter from markdown content."""
        if not content.startswith("---"):
            return {}

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}

        try:
            return yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            return {}
