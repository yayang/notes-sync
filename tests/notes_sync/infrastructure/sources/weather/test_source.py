from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from httpx import Response

from notes_sync.infrastructure.sources.weather.source import OpenMeteoSource


class TestOpenMeteoSource:
    @pytest.fixture
    def source(self):
        return OpenMeteoSource(lat=31.2, lon=121.4)

    def test_fetch_raw_data_success(self, source):
        start = date(2025, 1, 1)
        end = date(2025, 1, 1)

        # Mock Weather API response
        mock_response_weather = {
            "daily": {
                "time": ["2025-01-01"],
                "weathercode": [0],
                "temperature_2m_max": [15.5],
                "temperature_2m_min": [5.2],
            }
        }
        # Mock AQI API response
        mock_response_aqi = {
            "hourly": {
                "time": ["2025-01-01T00:00", "2025-01-01T01:00"],
                "us_aqi": [40, 50],
                "pm2_5": [10.5, 12.0],
            }
        }

        with patch("httpx.get") as mock_get:
            # Configure side_effect for multiple calls
            def side_effect(url, **kwargs):
                if "air-quality" in url:
                    return Response(200, json=mock_response_aqi, request=MagicMock())
                return Response(200, json=mock_response_weather, request=MagicMock())

            mock_get.side_effect = side_effect

            results = source.fetch_raw_data(start, end)

            assert isinstance(results, list)
            assert len(results) == 1
            raw_entry = results[0]
            assert isinstance(raw_entry, dict)
            assert "weather" in raw_entry
            assert "air_quality" in raw_entry
            assert raw_entry["weather"] == mock_response_weather
            assert raw_entry["air_quality"] == mock_response_aqi
            assert "pm2_5" in raw_entry["air_quality"]["hourly"]
            assert raw_entry["date"] == "2025-01-01"
