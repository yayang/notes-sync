import logging
from datetime import date
from typing import Any

import httpx

from notes_sync.core.protocols import DiarySyncContextSource

logger = logging.getLogger(__name__)


class NotionSyncContextSource(DiarySyncContextSource):
    def __init__(self, token: str, database_id: str):
        self.token = token
        self.database_id = database_id

    def _send_request(self, url: str, headers: dict, body: dict) -> dict:
        with httpx.Client() as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                raise Exception(f"Notion Query failed: {resp.status_code} {resp.text}")
            return resp.json()

    def _do_fetch(self, start_date: date, end_date: date) -> list[Any]:
        days_count = (end_date - start_date).days + 1
        page_size = max(1, days_count)

        url = f"https://api.notion.com/v1/databases/{self.database_id.replace('-', '')}/query"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        body = {
            "filter": {
                "and": [
                    {
                        "property": "Date",
                        "date": {"on_or_after": start_date.isoformat()},
                    },
                    {
                        "property": "Date",
                        "date": {"on_or_before": end_date.isoformat()},
                    },
                ]
            },
            "page_size": page_size,
        }

        data = self._send_request(url, headers, body)
        return data.get("results", [])
