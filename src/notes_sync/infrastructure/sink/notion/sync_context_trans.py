from datetime import date, datetime
from typing import Any, Optional

from notes_sync.core.protocols import DiarySyncContextTransformer
from notes_sync.infrastructure.sink.notion.mapping import DiaryKey
from notes_sync.models.models import DiarySyncContext


class NotionSyncContextTrans(DiarySyncContextTransformer):
    def to_context(self, raw_data: list[Any]) -> dict[date, DiarySyncContext]:
        result = {}
        for page in raw_data:
            cur_date = self.__extract_date(page)
            if not cur_date:
                continue

            props = page.get("properties", {})
            result[cur_date] = DiarySyncContext(
                remote_id=page.get("id"),
                status=self.__extract_select(props, DiaryKey.STATUS),
                steps=self.__extract_number(props, DiaryKey.STEPS),
            )

        return result

    def __extract_date(self, page: dict) -> Optional[date]:
        """Extract date from title with date mention."""
        props = page.get("properties", {})
        title_arr = props.get(DiaryKey.NAME, {}).get("title", [])

        for item in title_arr:
            if item.get("type") != "mention":
                continue
            start_str = item.get("mention", {}).get("date", {}).get("start")
            if not start_str:
                continue
            try:
                return datetime.strptime(start_str, "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    def __extract_select(self, props: dict, key: str) -> Optional[str]:
        return (props.get(key, {}).get("select") or {}).get("name")

    def __extract_number(self, props: dict, key: str) -> Optional[int]:
        return props.get(key, {}).get("number")
