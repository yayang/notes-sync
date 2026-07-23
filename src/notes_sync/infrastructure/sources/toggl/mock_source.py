from datetime import date
from typing import Any

from notes_sync.core.protocols import DiarySource


class TogglMockSource(DiarySource):
    def _do_fetch(self, start_date: date, end_date: date) -> list[Any]:
        """
        Returns mock data mimicking Toggl API response.
        Simulating a day with:
        - Work: 4 hours
        - Sleep: 8 hours
        - Entertainment: 2 hours
        """
        base_date = start_date.strftime("%Y-%m-%d")

        return [
            # 1. Sleep (00:00 - 08:00)
            {
                "id": 1001,
                "project_id": 101,  # Assuming 101 is mapped to Sleep
                "start": f"{base_date}T00:00:00+00:00",
                "stop": f"{base_date}T08:00:00+00:00",
                "duration": 28800,
                "description": "Sleep",
                "tags": [],
            },
            # 2. Work (09:00 - 13:00)
            {
                "id": 1002,
                "project_id": 102,
                "start": f"{base_date}T09:00:00+00:00",
                "stop": f"{base_date}T13:00:00+00:00",
                "duration": 14400,
                "description": "Coding Feature X",
                "tags": ["DeepWork"],
            },
            # 3. Entertainment (20:00 - 22:00)
            {
                "id": 1003,
                "project_id": 103,
                "start": f"{base_date}T20:00:00+00:00",
                "stop": f"{base_date}T22:00:00+00:00",
                "duration": 7200,
                "description": "Watch Movie",
                "tags": ["Relax"],
            },
        ]
