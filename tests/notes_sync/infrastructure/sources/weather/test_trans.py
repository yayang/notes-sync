from datetime import date

from notes_sync.infrastructure.sources.weather.trans import OpenMeteoTransformer
from notes_sync.models.models import WeatherStatus


class TestOpenMeteoTransformer:
    def test_transform_normal(self):
        trans = OpenMeteoTransformer()
        raw_data = [
            {
                "date": "2025-01-01",
                "weather": {
                    "daily": {
                        "time": ["2025-01-01"],
                        "weathercode": [0],  # Sunny
                        "temperature_2m_max": [25.0],
                        "temperature_2m_min": [15.0],
                    }
                },
                "air_quality": {"hourly": {"us_aqi": [50, 60]}},
            }
        ]

        result = trans.to_internal_model(raw_data)
        report = result[date(2025, 1, 1)]

        assert report.weather == WeatherStatus.SUNNY
        assert report.air_quality == 55

    def test_transform_hazy_upgrade(self):
        trans = OpenMeteoTransformer()
        raw_data = [
            {
                "date": "2025-01-01",
                "weather": {
                    "daily": {
                        "time": ["2025-01-01"],
                        "weathercode": [0],  # Sunny
                        "temperature_2m_max": [25.0],
                        "temperature_2m_min": [15.0],
                    }
                },
                "air_quality": {
                    "hourly": {
                        # Threshold is 125
                        "us_aqi": [130]
                    }
                },
            }
        ]

        result = trans.to_internal_model(raw_data)
        report = result[date(2025, 1, 1)]

        assert report.weather == WeatherStatus.HAZY

    def test_transform_extreme_aqi(self):
        trans = OpenMeteoTransformer()
        raw_data = [
            {
                "date": "2025-01-01",
                "weather": {
                    "daily": {
                        "time": ["2025-01-01"],
                        "weathercode": [0],  # Sunny
                        "temperature_2m_max": [25.0],
                        "temperature_2m_min": [15.0],
                    }
                },
                "air_quality": {
                    "hourly": {
                        # Threshold is 200
                        "us_aqi": [210]
                    }
                },
            }
        ]

        result = trans.to_internal_model(raw_data)
        report = result[date(2025, 1, 1)]

        assert report.weather == WeatherStatus.EXTREME

    def test_transform_extreme_temp_high(self):
        trans = OpenMeteoTransformer()
        raw_data = [
            {
                "date": "2025-01-01",
                "weather": {
                    "daily": {
                        "time": ["2025-01-01"],
                        "weathercode": [0],
                        "temperature_2m_max": [41.0],  # Threshold 40
                        "temperature_2m_min": [20.0],
                    }
                },
                "air_quality": {"hourly": {"us_aqi": [50]}},
            }
        ]

        result = trans.to_internal_model(raw_data)
        report = result[date(2025, 1, 1)]

        assert report.weather == WeatherStatus.EXTREME

    def test_transform_extreme_temp_low(self):
        trans = OpenMeteoTransformer()
        raw_data = [
            {
                "date": "2025-01-01",
                "weather": {
                    "daily": {
                        "time": ["2025-01-01"],
                        "weathercode": [0],
                        "temperature_2m_max": [5.0],
                        "temperature_2m_min": [-6.0],  # Threshold -5
                    }
                },
                "air_quality": {"hourly": {"us_aqi": [50]}},
            }
        ]

        result = trans.to_internal_model(raw_data)
        report = result[date(2025, 1, 1)]

        assert report.weather == WeatherStatus.EXTREME

    def test_transform_extreme_pm25(self):
        trans = OpenMeteoTransformer()
        raw_data = [
            {
                "date": "2025-01-01",
                "weather": {
                    "daily": {
                        "time": ["2025-01-01"],
                        "weathercode": [0],
                        "temperature_2m_max": [25.0],
                        "temperature_2m_min": [15.0],
                    }
                },
                "air_quality": {
                    "hourly": {
                        "us_aqi": [50],
                        "pm2_5": [160.0],  # Threshold 150
                    }
                },
            }
        ]

        result = trans.to_internal_model(raw_data)
        report = result[date(2025, 1, 1)]

        assert report.weather == WeatherStatus.EXTREME
        assert report.pm25 == 160
