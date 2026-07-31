from abc import ABC
from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

from notes_sync.models.schema import SinkName

"""
Status
"""


class SleepStatus(StrEnum):
    ON_TIME = "on_time"
    LITTLE_LATE = "a_little_late"
    TOO_LATE = "too_late"
    BAD_SLEEP = "bad_sleep"
    AFTER_NOON = "after_noon"


class WeatherStatus(StrEnum):
    SUNNY = "Sunny"
    CLOUDY = "Cloudy"
    RAINY = "Rainy"
    SNOWY = "Snowy"
    HAZY = "Hazy"
    EXTREME = "Extreme"
    UNDEFINED = "Undefined"


"""
Report
"""


class WeatherReport(BaseModel):
    temp_high: int
    temp_low: int
    weather: WeatherStatus = WeatherStatus.UNDEFINED
    air_quality: int = 0
    pm25: int = 0


class CategoryReport(BaseModel):
    total_seconds: float = 0.0
    breakdown: dict[str, float] = Field(default_factory=dict)


class SleepReport(BaseModel):
    bed_time: Optional[str] = None
    bed_status: Optional[SleepStatus] = None
    wake_time: Optional[str] = None
    wake_status: Optional[SleepStatus] = None
    linger_time: Optional[str] = None


class DiaryReport(BaseModel):
    time: dict[str, CategoryReport] = Field(default_factory=dict)
    sleep: SleepReport = Field(default_factory=SleepReport)
    weather: Optional[WeatherReport] = None
    summary: Optional[str] = None
    icon: Optional[str] = None
    steps: Optional[int] = None
    pics: list[str] = Field(default_factory=list)


"""
Model
"""


# BaseNote 必须继承 BaseModel 才能让子类生效
class BaseNote(BaseModel, ABC):
    remote_id: Optional[str] = None
    source: Optional[str] = None
    content: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TimeEntry(BaseModel):
    start: datetime
    end: datetime
    duration: Optional[int] = None
    content: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class DiarySyncContext(BaseModel):
    """
    Metadata fetched from a Sink for sync decisions.

    Note: `remote_id` here represents the **Sink-side** identity (e.g., Notion page_id,
    Obsidian file path).
    注意这里的 steps 用于写前验证, 与 DiaryReport 中的 steps 语义不同

    This is distinct from `Diary.remote_id` which represents
    **Source-side** identity (e.g., Toggl entry ID).
    """

    remote_id: Optional[str] = None  # Sink-side identity (Notion page_id, etc.)
    status: Optional[str] = None
    steps: Optional[int] = None


class Diary(BaseNote):
    date: datetime  # Required
    time_entries: list[TimeEntry] = Field(default_factory=list)
    report: DiaryReport = Field(default_factory=DiaryReport)
    sync_contexts: dict[SinkName, DiarySyncContext] = Field(default_factory=dict)
    status: Optional[str] = "current"
