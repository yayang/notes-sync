from abc import ABC, abstractmethod
from datetime import date
from enum import IntEnum
from typing import Any, Generic, TypeVar

from notes_sync.config.settings import get_settings
from notes_sync.core.decorators import retry_on_exception
from notes_sync.models.models import Diary, DiarySyncContext, WeatherReport
from notes_sync.models.schema import SyncDecision

# 定义泛型变量 T
T = TypeVar("T")


class DiarySource(ABC):
    def __init__(self):
        self.limit = get_settings().retry.limit
        self.delay = get_settings().retry.delay

    @abstractmethod
    def _do_fetch(self, start_date: date, end_date: date) -> list[Any]:
        """子类重写该方法"""
        pass

    @retry_on_exception
    def fetch_raw_data(self, start_date: date, end_date: date) -> list[Any]:
        """负责 I/O: 从 API 或文件读取原始数据"""
        """调用该方法"""
        return self._do_fetch(start_date, end_date)


class DiarySourceTransformer(ABC):
    @abstractmethod
    def to_internal_model(self, raw_data: list[Any]) -> dict[date, Diary]:
        """负责解耦: 将原始 JSON 转为系统内部的 Note/Diary 对象"""
        pass


class DiarySyncGuard(ABC):
    @abstractmethod
    def evaluate(self, diary: Diary, context: DiarySyncContext) -> SyncDecision:
        """评估同步策略：根据日记数据和嵌入的元数据逻辑性地返回同步动作"""
        pass


class DiarySinkTransformer(ABC, Generic[T]):
    @abstractmethod
    def transform(self, diary: Diary, sync_decision: SyncDecision) -> T:
        """负责解耦: 根据日记数据生成目标端格式"""
        pass


class DiarySink(ABC, Generic[T]):
    @abstractmethod
    def sink_data(
        self,
        diary_date: date,
        data: T,
        context: DiarySyncContext,
        sync_decision: SyncDecision,
    ) -> None:
        """负责 I/O: 将格式化后的数据保存到文件或调用API"""
        pass


# SyncContext
class DiarySyncContextSource(DiarySource):
    pass


class DiarySyncContextTransformer(ABC):
    @abstractmethod
    def to_context(self, raw_data: list[Any]) -> dict[date, DiarySyncContext]:
        """
        [感知层] 获取下游平台指定日期的现有元数据
        返回值示例: {"status": "archived", "steps": 5000}
        """
        pass


# Enricher
class WeatherSourceTransformer(ABC):
    @abstractmethod
    def to_internal_model(self, raw_data: list[Any]) -> dict[date, WeatherReport]:
        """负责解耦: 将原始 JSON 转为系统内部的 Weather 对象"""
        pass


class EnricherPriority(IntEnum):
    HIGH = 10  # 执行顺序: 优先 (Producers)
    DEFAULT = 100  # 执行顺序: 默认 (Standard Processors)
    LOW = 200  # 执行顺序: 最后 (Aggregators/Consumers)


class DiaryEnricher(ABC):
    priority: EnricherPriority = EnricherPriority.DEFAULT

    @abstractmethod
    def enrich(self, mapping: dict[date, Diary], start: date, end: date) -> None:
        """
        附属源契约: 根据远端元数据逻辑性地『修改』已有日记对象
        """
        pass
