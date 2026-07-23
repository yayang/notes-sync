import logging
from datetime import date, datetime

from notes_sync.core.builder import SinkProvider
from notes_sync.models.models import Diary, DiarySyncContext
from notes_sync.models.schema import SyncAction, SyncDecision

logger = logging.getLogger(__name__)


class CreateDiaryWorkflow:
    """Create a blank diary only when a sink has no entry for the date."""

    def __init__(self, sink_providers: list[SinkProvider]):
        self.sink_providers = sink_providers

    def run(self, diary_date: date) -> None:
        diary = Diary(date=datetime.combine(diary_date, datetime.min.time()))
        failures = []

        for provider in self.sink_providers:
            try:
                self.__create_missing(provider, diary, diary_date)
            except Exception as error:
                logger.exception(
                    "[CreateDiaryError] %s failed for %s",
                    provider.name,
                    diary_date,
                )
                failures.append(f"{provider.name}: {error}")

        if failures:
            raise RuntimeError("; ".join(failures))

    def __create_missing(
        self,
        provider: SinkProvider,
        diary: Diary,
        diary_date: date,
    ) -> None:
        raw_contexts = provider.ctx_source.fetch_raw_data(diary_date, diary_date)
        contexts = provider.ctx_trans.to_context(raw_contexts)
        context = contexts.get(diary_date) or DiarySyncContext()
        if context.remote_id:
            logger.info("[%s] Diary already exists for %s", provider.name, diary_date)
            return

        diary.sync_contexts[provider.name] = context
        decision = SyncDecision(action=SyncAction.CREATE)
        data = provider.s_trans.transform(diary, decision)
        provider.sink.sink_data(diary_date, data, context, decision)
