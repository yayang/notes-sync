from enum import StrEnum


class DiaryKey(StrEnum):
    FOCUS_HOURS = "focus_hours"
    PLAY_HOURS = "play_hours"
    SLEEP_HOURS = "sleep_hours"
    ROUTINE_HOURS = "routine_hours"
    STATUS = "status"
    TAGS = "tags"
    DATE = "date"
    BED_TIME_PREV = "bed_time_prev"
    BED_STATUS_PREV = "bed_status_prev"
    GETUP_TIME = "getup_time"
    GETUP_STATUS = "getup_status"
    STEPS = "steps"
    UNRECORDED_HOURS = "unrecorded_hours"
    LINGER_MINUTES = "linger_minutes"
    TEMP_HIGH = "temp_high"
    TEMP_LOW = "temp_low"
    WEATHER = "weather"
    AIR_QUALITY = "air_quality"
    PM25 = "pm2.5"


class SectionKey(StrEnum):
    STATISTICS = "## 📊 Statistics"
    TIME_ENTRIES = "## Time Entries"
    USER_RECORD = "## 📝 记录"


# Header = "# 2026-01-03 星期六"


UserSection = f"""{SectionKey.USER_RECORD}
- 今日核心: 
    - 今日交付: 
    - 未交付原因: 
- 进步:
    - 
- 生活:
    - 

## 🔍 复盘
- 

## 💭 感悟
- 

## ⚡️ 行动
- [ ] 
"""
