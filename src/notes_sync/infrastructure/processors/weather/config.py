from notes_sync.models.models import WeatherStatus

# WMO Weather interpretation codes (WW)
# https://open-meteo.com/en/docs
# 核心逻辑： 将“强度差异”收拢为“性质差异”

# WMO (World Meteorological Organization) Code 映射表
WMO_CODE_MAP = {
    # Sunny: 晴朗
    0: WeatherStatus.SUNNY,
    # Cloudy: 多云、 阴天
    1: WeatherStatus.CLOUDY,
    2: WeatherStatus.CLOUDY,
    3: WeatherStatus.CLOUDY,
    # Hazy: 雾 (能见度受限)
    45: WeatherStatus.HAZY,
    48: WeatherStatus.HAZY,
    # Rainy: 阵雨、 细雨、 大雨 (液态降水)
    51: WeatherStatus.RAINY,
    53: WeatherStatus.RAINY,
    55: WeatherStatus.RAINY,
    61: WeatherStatus.RAINY,
    63: WeatherStatus.RAINY,
    65: WeatherStatus.RAINY,
    80: WeatherStatus.RAINY,
    81: WeatherStatus.RAINY,
    82: WeatherStatus.RAINY,
    # Snowy: 雪、 阵雪 (固态降水)
    71: WeatherStatus.SNOWY,
    73: WeatherStatus.SNOWY,
    75: WeatherStatus.SNOWY,
    77: WeatherStatus.SNOWY,
    85: WeatherStatus.SNOWY,
    86: WeatherStatus.SNOWY,
    # Extreme: 冻雨、 雷暴 (物理危险或性质改变)
    56: WeatherStatus.EXTREME,  # Freezing Drizzle
    57: WeatherStatus.EXTREME,  # Freezing Drizzle: Dense
    66: WeatherStatus.EXTREME,  # Freezing Rain: Light
    67: WeatherStatus.EXTREME,  # Freezing Rain: Heavy
    95: WeatherStatus.EXTREME,  # Thunderstorm
    96: WeatherStatus.EXTREME,  # Thunderstorm with Hail
    99: WeatherStatus.EXTREME,  # Thunderstorm with Heavy Hail
}

# SUNNY -> Hazy 升级
SUNNY_HAZY_THRESHOLD = 125

# 闭区间, 任意状态 -> Extreme 升级
EXTREME_CONFIG = {
    "aqi_threshold": 200,
    "temp_high_threshold": 40,
    "temp_low_threshold": -5,
    "pm2.5_threshold": 150,
}


def get_weather_status(code: int) -> WeatherStatus:
    return WMO_CODE_MAP.get(code, WeatherStatus.UNDEFINED)
