import logging
from datetime import date, datetime, timedelta

from notes_sync.config.settings import get_settings
from notes_sync.core.builder import SinkProvider, SourceProvider
from notes_sync.core.protocols import (
    DiaryEnricher,
    DiarySyncGuard,
)
from notes_sync.models.models import Diary, DiarySyncContext
from notes_sync.models.schema import SyncAction

logger = logging.getLogger(__name__)


class SyncDiaryWorkflow:
    def __init__(
        self,
        source_provider: SourceProvider,
        enrichers: list[DiaryEnricher],
        sync_guard: DiarySyncGuard,
        sink_providers: list[SinkProvider],
    ):
        self.source = source_provider.source
        self.s_trans = source_provider.s_trans
        self.sync_guard = sync_guard
        self.enrichers = enrichers
        self.sink_providers = sink_providers

    def run(self, days: int):
        # 1. Date Slicing
        start_date = date.today() - timedelta(days=days)
        earliest_date = date.fromisoformat(get_settings().EARLIEST_SYNC_DATE)
        start_date = max(start_date, earliest_date)
        end_date = date.today()

        logger.info(f"--- Starting Sync for {start_date} to {end_date} ---")

        # 2. Execute Sync Cycle
        self._execute_sync_cycle(start_date, end_date)

    def _execute_sync_cycle(self, start: date, end: date):
        try:
            # Step 1: Fetch Raw Data
            raw_data = self.source.fetch_raw_data(start, end)
            # Step 2: Source -> Internal Model
            base_mapping = self.s_trans.to_internal_model(raw_data)

            # Hydrate missing dates for the full range
            self._hydrate_missing_dates(base_mapping, start, end)

            # Step 3: Enrich
            for enricher in self.enrichers:
                enricher.enrich(base_mapping, start, end)

            # Step 4 & 5: Process Sinks (Strategy + Transform + Sink)
            self._process_sink_providers(base_mapping, start, end)

        except Exception as e:
            logger.critical(f"[FatalError] Cycle failed for {start}: {e}")
            raise

    def _hydrate_missing_dates(
        self, base_mapping: dict[date, Diary], start: date, end: date
    ) -> None:
        """
        Ensure `base_mapping` contains a Diary object for every date from start to end.
        If a date is missing (e.g., no time entries in Toggl), create an empty placeholder Diary.
        """

        curr = start
        while curr <= end:
            if curr not in base_mapping:
                base_mapping[curr] = Diary(
                    date=datetime.combine(curr, datetime.min.time()),
                    time_entries=[],
                )
            curr += timedelta(days=1)

    def _process_sink_providers(
        self, base_mapping: dict[date, Diary], start: date, end: date
    ):
        failures = []
        for chnl in self.sink_providers:
            try:
                # 1. Fetch Remote Context
                ctx_raw = chnl.ctx_source.fetch_raw_data(start, end)
                contexts = chnl.ctx_trans.to_context(ctx_raw)

                # 2. Evaluate & Transform & Sink
                for d, diary in base_mapping.items():
                    context = (
                        contexts.get(d) or DiarySyncContext()
                    )  # Ensure context is not None
                    diary.sync_contexts[chnl.name] = context

                    # Guard evaluates global policy (returns SyncDecision)
                    sync_decision = self.sync_guard.evaluate(diary, context)
                    if sync_decision.action == SyncAction.SKIP:
                        continue

                    # Transform uses SyncDecision
                    transformed_data = chnl.s_trans.transform(diary, sync_decision)

                    # 3. Sink (Per item)
                    try:
                        chnl.sink.sink_data(d, transformed_data, context, sync_decision)
                    except Exception as e:
                        logger.error(f"[SinkError] {chnl.name} failed for {d}: {e}")
                        failures.append(f"{chnl.name}/{d}: {e}")

            except Exception as e:
                logger.error(f"[ProviderError] {chnl.name} failed: {e}")
                failures.append(f"{chnl.name}: {e}")

        if failures:
            raise RuntimeError("; ".join(failures))
