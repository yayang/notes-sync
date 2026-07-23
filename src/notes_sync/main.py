import logging
from datetime import date

from notes_sync.config.settings import get_settings
from notes_sync.core.builder import (
    get_enrichers,
    get_sink_providers,
    get_source_provider,
)
from notes_sync.core.create_diary_workflow import CreateDiaryWorkflow
from notes_sync.core.diary_workflow import SyncDiaryWorkflow
from notes_sync.core.guard import DefaultDiarySyncGuard
from notes_sync.core.logger import setup_logging
from notes_sync.models.schema import SinkName, SourceName

logger = logging.getLogger("notes_sync")


def run_sync_task(settings):
    """执行一次完整的同步任务"""
    source_provider = get_source_provider(SourceName.TOGGL)

    enrichers = get_enrichers(source_provider)

    sink_providers = get_sink_providers([SinkName.NOTION, SinkName.OBSIDIAN])

    workflow = SyncDiaryWorkflow(
        source_provider,
        enrichers,
        DefaultDiarySyncGuard(),
        sink_providers,
    )
    workflow.run(days=settings.LOOKBACK_WINDOW_DAYS)


def main(settings=None):
    if settings is None:
        settings = get_settings()

    setup_logging(settings.log)

    run_sync_task(settings)


def create_diary(settings=None, diary_date: date | None = None):
    """Create today's missing diary entries without running sync enrichers."""
    if settings is None:
        settings = get_settings()

    setup_logging(settings.log)
    workflow = CreateDiaryWorkflow(
        get_sink_providers([SinkName.NOTION, SinkName.OBSIDIAN])
    )
    workflow.run(diary_date or date.today())


if __name__ == "__main__":
    main()
