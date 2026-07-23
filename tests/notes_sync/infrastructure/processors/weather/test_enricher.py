from datetime import date
from unittest.mock import MagicMock

from notes_sync.infrastructure.processors.weather.enricher import WeatherEnricher
from notes_sync.models.models import Diary, WeatherReport, WeatherStatus


def test_weather_enricher_populates_diary():
    # Setup
    enricher = WeatherEnricher()

    # Mock source to return specific weather data
    mock_weather_data = WeatherReport(
        temp_high=30, temp_low=20, weather=WeatherStatus.SUNNY, air_quality=50
    )
    # Mock source fetch and trans
    enricher.source = MagicMock()
    enricher.source.fetch_raw_data.return_value = []  # Raw data doesn't matter if we mock trans

    enricher.trans = MagicMock()
    # Return map: date -> WeatherReport
    enricher.trans.to_internal_model.return_value = {
        date(2026, 1, 1): mock_weather_data
    }

    diary = Diary(date=date(2026, 1, 1))
    mapping = {date(2026, 1, 1): diary}

    # Action
    enricher.enrich(mapping, date(2026, 1, 1), date(2026, 1, 1))

    # Assert
    assert diary.report.weather == mock_weather_data
    assert diary.report.weather.temp_high == 30
