from pydantic import BaseModel


class SleepConfig(BaseModel):
    """
    ### A. 入睡识别 (Go to Bed)
    1. 晚间入睡：检索昨日 20:00 后的最后一个 "💤 Sleep" 条目。
    2. 凌晨入睡：若昨日未记录，检索当日 12:00 前的首个 "💤 Sleep" 条目。
    入睡状态判定：
    - on_time: 晚间入睡 (>= 20:00) 或凌晨 00:30 前
    - a_little_late: 00:30 ~ 01:30
    - too_late: 01:30 ~ 03:00
    - bad_sleep: 03:00 之后

    ### B. 起床识别 (Get Up)
    - 优先级：当日 04:00 后首个 "起床/Get up" 动作 > 首个睡眠条目结束时间。
    起床状态判定：
    - on_time: < 08:30 (早起)
    - a_little_late: 08:30 ~ 09:30 (正常)
    - too_late: 09:30 ~ 12:00 (偏晚)
    - after_noon: >= 12:00 (极晚)

    ### C. 赖床时间
    在有起床时间的情况下, 找到他之前的第一个"💤 Sleep" 条目的end, 并计算.
    """

    # Gotobed Thresholds
    gotobed_on_time: str = "00:30"
    gotobed_late: str = "01:30"
    gotobed_too_late: str = "03:00"

    # Getup Thresholds
    getup_on_time: str = "08:30"
    getup_late: str = "09:30"
    getup_too_late: str = "12:00"

    # Operational Thresholds (replacing hardcodes)
    earliest_sleep_hour_yd: int = 20
    latest_sleep_hour: int = 12
    earliest_getup_hour: int = 4
    linger_threshold_max: int = 360

    getup_keys: set[str] = {"起床", "Get up"}

    category: str = "💤 Sleep"
