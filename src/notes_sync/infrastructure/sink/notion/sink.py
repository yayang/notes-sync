import json
import logging
from datetime import date
from math import inf
from time import monotonic
from typing import Any

import httpx

from notes_sync.core.protocols import (
    SINK_RETRY_DELAY_SECONDS,
    DiarySink,
    RetryableSinkError,
)
from notes_sync.infrastructure.sink.notion.mapping import DiaryKey
from notes_sync.models.models import DiarySyncContext
from notes_sync.models.schema import SyncAction, SyncDecision

logger = logging.getLogger(__name__)

_RICH_TEXT_CONTENT_LIMIT = 2000
_RICH_TEXT_ARRAY_LIMIT = 100


class NotionSink(DiarySink[dict[str, Any]]):
    """Notion API Sink with CREATE/UPDATE logic."""

    def __init__(self, token: str, db_id: str):
        self.token = token
        self.db_id = db_id.replace("-", "")
        self._writes_paused_until = 0.0
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
                notion_props[key] = {"rich_text": self.__rich_text(key, value)}

        return notion_props

    def __rich_text(self, key: str, value: str) -> list[dict[str, dict[str, str]]]:
        """Keep each chunk within the limit even when counted as UTF-16."""
        chunks = []
        start = units = 0
        for index, char in enumerate(value):
            width = 2 if ord(char) > 0xFFFF else 1
            if units + width > _RICH_TEXT_CONTENT_LIMIT:
                chunks.append(value[start:index])
                if len(chunks) == _RICH_TEXT_ARRAY_LIMIT:
                    raise ValueError(
                        f"Notion rich text for {key} exceeds {_RICH_TEXT_ARRAY_LIMIT} elements"
                    )
                start = index
                units = 0
            units += width
        chunks.append(value[start:])
        return [{"text": {"content": chunk}} for chunk in chunks]

    def __send_request(self, method: str, url: str, body: dict) -> dict:
        if monotonic() < self._writes_paused_until:
            raise RuntimeError("Notion write deferred by rate limit")

        with httpx.Client() as client:
            try:
                resp = client.request(
                    method, url, headers=self._headers, content=json.dumps(body)
                )
            except (httpx.ConnectError, httpx.ConnectTimeout) as error:
                raise RetryableSinkError(f"Notion connection failed: {error}") from error

        if resp.status_code in (200, 201):
            return resp.json()

        logger.error(f"[NotionSink] {method} failed: {resp.status_code} {resp.text}")
        message = f"Notion API failed: {resp.status_code}"
        if resp.status_code == 429:
            delay = self.__rate_limit_delay(resp)
            self._writes_paused_until = monotonic() + delay
            if delay <= SINK_RETRY_DELAY_SECONDS:
                raise RetryableSinkError(message)
        raise RuntimeError(message)

    def __rate_limit_delay(self, response: httpx.Response) -> float:
        """Return the cooldown or defer writes for the rest of this run."""
        try:
            delay = float(int(response.headers.get("Retry-After", "")))
            error = response.json()
        except (ValueError, OverflowError):
            return inf
        if not isinstance(error, dict) or delay < 0:
            return inf
        details = error.get("additional_data")
        if (
            isinstance(details, dict)
            and details.get("rate_limit_reason") == "public_api_request_blocked"
        ):
            return inf
        return delay
