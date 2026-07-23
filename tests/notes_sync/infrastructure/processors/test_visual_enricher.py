from datetime import date
from unittest.mock import MagicMock, patch

from notes_sync.infrastructure.processors.visual_enricher import VisualEnricher
from notes_sync.models.models import Diary


def test_visual_enricher_sets_icon():
    # Setup
    with patch(
        "notes_sync.infrastructure.processors.visual_enricher.get_settings"
    ) as mock_settings:
        mock_settings.return_value = MagicMock(DATE_ICON_BASE_URL="http://icon.com/")

        enricher = VisualEnricher()
        diary = Diary(date=date(2026, 1, 5))
        mapping = {date(2026, 1, 5): diary}

        # Action
        enricher.enrich(mapping, date(2026, 1, 1), date(2026, 1, 6))

        # Assert
        assert diary.report.icon == "http://icon.com/date_05.png"
