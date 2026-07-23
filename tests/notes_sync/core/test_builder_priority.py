from datetime import date

from notes_sync.core.builder import get_enrichers
from notes_sync.core.protocols import (
    DiarySource,
    DiarySourceTransformer,
    EnricherPriority,
)
from notes_sync.infrastructure.processors.statistics.enricher import StatisticsEnricher
from notes_sync.infrastructure.processors.summary.enricher import SummaryEnricher


class MockSource(DiarySource):
    def _do_fetch(self, start_date: date, end_date: date):
        return []


class MockTrans(DiarySourceTransformer):
    def to_internal_model(self, raw_data):
        return {}


class MockProvider:
    def __init__(self):
        self.source = MockSource()
        self.s_trans = MockTrans()


def test_enricher_priority_sorting():
    """Verify that enrichers are sorted by priority."""
    provider = MockProvider()
    enrichers = get_enrichers(provider)

    # Find indices of key enrichers
    stats_idx = -1
    summary_idx = -1

    for i, e in enumerate(enrichers):
        if isinstance(e, StatisticsEnricher):
            stats_idx = i
        elif isinstance(e, SummaryEnricher):
            summary_idx = i

    # Statistics (HIGH=10) MUST be before Summary (Default=100)
    # Even though user removed priority=LOW from Summary, Stats(10) < Summary(100) is still true.
    assert stats_idx != -1
    assert summary_idx != -1
    assert stats_idx < summary_idx

    # Check stable sort
    # StepsEnricher is defined BEFORE SleepEnricher in builder.py LIST, and both have DEFAULT priority.
    # So Steps MUST appear BEFORE Sleep in the final list.
    steps_enricher = next(
        e for e in enrichers if e.__class__.__name__ == "StepsEnricher"
    )
    sleep_enricher = next(
        e for e in enrichers if e.__class__.__name__ == "SleepEnricher"
    )

    steps_idx = enrichers.index(steps_enricher)
    sleep_idx = enrichers.index(sleep_enricher)

    assert steps_idx < sleep_idx

    # Explicitly check values
    stats_enricher = next(e for e in enrichers if isinstance(e, StatisticsEnricher))
    assert stats_enricher.priority == EnricherPriority.HIGH
