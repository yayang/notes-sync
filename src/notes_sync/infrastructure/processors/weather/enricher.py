import logging
from datetime import date

from notes_sync.config.settings import get_settings
from notes_sync.core.protocols import DiaryEnricher
from notes_sync.infrastructure.sources.weather.source import OpenMeteoSource
from notes_sync.infrastructure.sources.weather.trans import OpenMeteoTransformer
from notes_sync.models.models import Diary

logger = logging.getLogger(__name__)


class WeatherEnricher(DiaryEnricher):
    def __init__(self):
        settings = get_settings()
        self.source = OpenMeteoSource(
            settings.LATITUDE,
            settings.LONGITUDE,
            settings.CACHE_DIR,
        )
        self.trans = OpenMeteoTransformer()

    def enrich(self, mapping: dict[date, Diary], start: date, end: date):
        """
        Enrich diaries with weather data.
        """
        try:
            # 1. Fetch raw data
            raw_list = self.source.fetch_raw_data(start, end)

            # 2. Transform to internal models
            weather_map = self.trans.to_internal_model(raw_list)

            # 3. Apply to diaries
            for day, weather_data in weather_map.items():
                if day in mapping:
                    diary = mapping[day]
                    # Update DiaryReport (Weather moved from Extension to Report)
                    diary.report.weather = weather_data
        except Exception as e:
            logger.warning(f"[WeatherEnricher] Enrichment failed for {start} to {end}, skipping. Reason: {e}")
