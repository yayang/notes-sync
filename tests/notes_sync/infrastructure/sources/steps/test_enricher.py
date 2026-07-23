from datetime import date

from notes_sync.infrastructure.processors.step_enricher import StepsEnricher
from notes_sync.infrastructure.sources.steps.source import StepsSource
from notes_sync.models.models import Diary, DiaryReport


def test_steps_enricher_single_entry_flow(tmp_path):
    # 1. Prepare data via source
    steps_file = tmp_path / "health_data.txt"
    raw_data = "2026-01-02,1989"
    steps_file.write_text(raw_data)

    source = StepsSource(steps_file)
    enricher = StepsEnricher(source)

    # 2. Setup diary mapping
    diary = Diary(date=date(2026, 1, 2), report=DiaryReport(steps=0))
    mapping = {date(2026, 1, 2): diary}

    # 3. Enrich
    enricher.enrich(mapping, date(2026, 1, 1), date(2026, 1, 3))

    # 4. Assert
    assert mapping[date(2026, 1, 2)].report.steps == 1989


def test_steps_enricher_invalid_json(tmp_path):
    steps_file = tmp_path / "invalid.csv"
    steps_file.write_text("invalid csv content")

    source = StepsSource(steps_file)
    enricher = StepsEnricher(source)

    diary = Diary(date=date(2026, 1, 2), report=DiaryReport(steps=100))
    mapping = {date(2026, 1, 2): diary}

    # Should handle gracefully via source
    enricher.enrich(mapping, date(2026, 1, 1), date(2026, 1, 3))
    assert mapping[date(2026, 1, 2)].report.steps == 100
