from datetime import date

from notes_sync.config.settings import get_settings
from notes_sync.core.protocols import DiaryEnricher
from notes_sync.models.models import Diary


class VisualEnricher(DiaryEnricher):
    def enrich(self, base_mapping: dict[date, Diary], start: date, end: date):
        """
        根据日期生成对应的图标 URL
        Args:
            Diary: 日期对象
        """
        for d, diary in base_mapping.items():
            day = d.day
            diary.report.icon = f"{get_settings().DATE_ICON_BASE_URL}date_{day:02d}.png"
