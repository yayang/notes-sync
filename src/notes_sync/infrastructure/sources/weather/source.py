import logging
from datetime import date, timedelta
from typing import Any, ClassVar

import httpx
from notes_sync.core.protocols import DiarySource

logger = logging.getLogger(__name__)


class OpenMeteoSource(DiarySource):
    """
    Source for fetching weather data from Open-Meteo API.
    Uses Archive API for historical data.
    """

    ARCHIVE_URL: ClassVar[str] = "https://archive-api.open-meteo.com/v1/archive"
    FORECAST_URL: ClassVar[str] = "https://api.open-meteo.com/v1/forecast"
    AIR_QUALITY_URL: ClassVar[str] = (
        "https://air-quality-api.open-meteo.com/v1/air-quality"
    )

    def __init__(self, lat: float, lon: float, cache_dir=None):
        self.lat = lat
        self.lon = lon
        self.cache_dir = cache_dir  # Placeholder for future caching

    def _do_fetch(self, start_date: date, end_date: date) -> list[Any]:
        """Fetch weather data for a date range. Returns list of dicts."""
        # OpenMeteo supports single call for range, but we need to unify archive/forecast logic.
        # For simplicity and correct logic (archive vs forecast), we iterate by day.

        results = []
        current = start_date
        while current <= end_date:
            data = self._fetch_single_day(current)
            if data:
                data["date"] = current.isoformat()
                results.append(data)
            current += timedelta(days=1)

        return results

    def _fetch_single_day(self, day: date) -> dict | None:
        if day < date.today():
            url = self.ARCHIVE_URL
        else:
            url = self.FORECAST_URL

        params: dict[str, Any] = {
            "latitude": self.lat,
            "longitude": self.lon,
            "start_date": day.isoformat(),
            "end_date": day.isoformat(),
            "daily": "weathercode,temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
        }

        # Weather Request
        resp_weather = httpx.get(url, params=params, timeout=10.0)
        resp_weather.raise_for_status()
        data_w = resp_weather.json()

        # 2. Fetch Air Quality
        params_aq: dict[str, Any] = {
            "latitude": self.lat,
            "longitude": self.lon,
            "start_date": day.isoformat(),
            "end_date": day.isoformat(),
            "hourly": "us_aqi,pm2_5",
            "timezone": "auto",
        }
        resp_aq = httpx.get(self.AIR_QUALITY_URL, params=params_aq, timeout=10.0)
        resp_aq.raise_for_status()
        data_aq = resp_aq.json()

        return {
            "weather": data_w,
            "air_quality": data_aq,
        }
