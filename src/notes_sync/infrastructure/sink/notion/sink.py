import json
import logging
from datetime import date
from typing import Any

import httpx

from notes_sync.core.protocols import DiarySink
from notes_sync.infrastructure.sink.notion.mapping import DiaryKey
from notes_sync.models.models import DiarySyncContext
from notes_sync.models.schema import SyncAction, SyncDecision

logger = logging.getLogger(__name__)


class NotionSink(DiarySink[dict[str, Any]]):
    """Notion API Sink with CREATE/UPDATE logic."""

    def __init__(self, token: str, db_id: str):
        self.token = token
        self.db_id = db_id.replace("-", "")
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    def sink_data(
        self,
        diary_date: date,
        data: dict[str, Any],
        context: DiarySyncContext,
        sync_decision: SyncDecision,
    ) -> None:
        if sync_decision.action == SyncAction.UPDATE:
            if context.remote_id is not None:
                self._update_page(context.remote_id, data)
        elif sync_decision.action == SyncAction.CREATE:
            self._create_page(diary_date, data)

    def _create_page(self, diary_date: date, props: dict[str, Any]) -> None:
        """POST to create a new page in Notion database."""
        url = "https://api.notion.com/v1/pages"
        body = {
            "parent": {"database_id": self.db_id},
            "properties": self.__build_notion_properties(diary_date, props),
        }
        if icon := props.get(DiaryKey.ICON):
            body["icon"] = {"type": "external", "external": {"url": icon}}

        self.__send_request("POST", url, body)
        logger.info(f"[NotionSink] Created page for {diary_date}")

    def _update_page(self, page_id: str, props: dict[str, Any]) -> None:
        """PATCH to update an existing Notion page."""
        url = f"https://api.notion.com/v1/pages/{page_id}"
        body = {"properties": self.__build_notion_properties(None, props)}

        if icon := props.get(DiaryKey.ICON):
            body["icon"] = {"type": "external", "external": {"url": icon}}

        self.__send_request("PATCH", url, body)
        logger.info(f"[NotionSink] Updated page {page_id}")

    # Keys that need select type formatting
    _SELECT_KEYS = {
        DiaryKey.BED_STATUS_PREV,
        DiaryKey.GETUP_STATUS,
        DiaryKey.WEATHER,
        DiaryKey.STATUS,
    }

    def __build_notion_properties(
        self, diary_date: date | None, props: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert flat props dict to Notion API property format."""
        notion_props: dict[str, Any] = {}

        # Title property - Name (only for create, using date mention)
        if diary_date:
            notion_props[DiaryKey.NAME] = {
                "title": [
                    {
                        "type": "mention",
                        "mention": {
                            "type": "date",
                            "date": {"start": diary_date.isoformat()},
                        },
                    }
                ]
            }
            # Also set Date property
            notion_props[DiaryKey.DATE] = {"date": {"start": diary_date.isoformat()}}

        for key, value in props.items():
            if key == DiaryKey.ICON:
                continue

            if key in self._SELECT_KEYS:
                # Select type (for status fields)
                notion_props[key] = {"select": {"name": str(value)}}
            elif isinstance(value, (int, float)):
                # Number type
                notion_props[key] = {"number": value}
            elif isinstance(value, str):
                # Rich text type (for time strings)
                notion_props[key] = {"rich_text": [{"text": {"content": value}}]}

        return notion_props

    def __send_request(self, method: str, url: str, body: dict) -> dict:
        body_str = json.dumps(body)
        # logger.debug(
        #     f"[NotionSink] Method: {method}, URL Len: {len(url)}, Body Len: {len(body_str)}"
        # )

        with httpx.Client() as client:
            if method == "POST":
                resp = client.post(url, headers=self._headers, content=body_str)
            else:
                resp = client.patch(url, headers=self._headers, content=body_str)

            if resp.status_code not in (200, 201):
                logger.error(
                    f"[NotionSink] {method} failed: {resp.status_code} {resp.text}"
                )
                raise Exception(f"Notion API failed: {resp.status_code}")
            return resp.json()
