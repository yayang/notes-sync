from datetime import date
from typing import Any

from notes_sync.core.protocols import WeatherSourceTransformer
from notes_sync.infrastructure.processors.weather.config import (
    EXTREME_CONFIG,
    SUNNY_HAZY_THRESHOLD,
    get_weather_status,
)
from notes_sync.models.models import WeatherReport, WeatherStatus


class OpenMeteoTransformer(WeatherSourceTransformer):
    def to_internal_model(self, raw_data: list[Any]) -> dict[date, WeatherReport]:
        result = {}
        for entry in raw_data:
            day_str = entry.get("date")
            if not day_str:
                continue

            day = date.fromisoformat(day_str)

            # Extract Weather Data
            weather_daily = entry.get("weather", {}).get("daily", {})
            if not weather_daily or not weather_daily.get("time"):
                continue

            # Assuming single day data per entry
            idx = 0
            temp_high = weather_daily["temperature_2m_max"][idx]
            temp_low = weather_daily["temperature_2m_min"][idx]
            wmo_code = weather_daily["weathercode"][idx]

            if temp_high is None or temp_low is None or wmo_code is None:
                continue

            # Extract Air Quality Data
            aqi_val = 0
            pm25_val = 0
            hourly = entry.get("air_quality", {}).get("hourly", {})
            if hourly:
                if "us_aqi" in hourly:
                    hourly_aqi = [x for x in hourly["us_aqi"] if x is not None]
                    if hourly_aqi:
                        aqi_val = int(sum(hourly_aqi) / len(hourly_aqi))

                if "pm2_5" in hourly:
                    hourly_pm = [x for x in hourly["pm2_5"] if x is not None]
                    if hourly_pm:
                        pm25_val = int(sum(hourly_pm) / len(hourly_pm))

            # Determine Status with Config Logic
            status = get_weather_status(int(wmo_code))

            # Logic 1: Sunny -> Hazy if AQI is high
            if status == WeatherStatus.SUNNY and aqi_val >= SUNNY_HAZY_THRESHOLD:
                status = WeatherStatus.HAZY

            # Logic 2: Extreme Check
            is_extreme = False
            # Check thresholds
            if aqi_val >= EXTREME_CONFIG["aqi_threshold"]:
                is_extreme = True
            elif pm25_val >= EXTREME_CONFIG.get("pm2.5_threshold", 999):
                is_extreme = True
            elif temp_high >= EXTREME_CONFIG["temp_high_threshold"]:
                is_extreme = True
            elif temp_low <= EXTREME_CONFIG["temp_low_threshold"]:
                is_extreme = True

            if is_extreme:
                status = WeatherStatus.EXTREME

            result[day] = WeatherReport(
                temp_high=int(round(temp_high)),
                temp_low=int(round(temp_low)),
                weather=status,
                air_quality=aqi_val,
                pm25=pm25_val,
            )
        return result
