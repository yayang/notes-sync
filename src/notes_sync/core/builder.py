import logging

from notes_sync.config.settings import get_settings
from notes_sync.core.protocols import (
    DiaryEnricher,
    DiarySink,
    DiarySinkTransformer,
    DiarySource,
    DiarySourceTransformer,
    DiarySyncContextSource,
    DiarySyncContextTransformer,
)
from notes_sync.infrastructure.processors.sleep.enricher import SleepEnricher
from notes_sync.infrastructure.processors.statistics.enricher import StatisticsEnricher
from notes_sync.infrastructure.processors.step_enricher import StepsEnricher
from notes_sync.infrastructure.processors.summary.enricher import SummaryEnricher
from notes_sync.infrastructure.processors.visual_enricher import VisualEnricher
from notes_sync.infrastructure.processors.weather.enricher import WeatherEnricher
from notes_sync.infrastructure.sink.notion.sink import NotionSink
from notes_sync.infrastructure.sink.notion.sink_trans import NotionDiaryTrans
from notes_sync.infrastructure.sink.notion.sync_context_source import (
    NotionSyncContextSource,
)
from notes_sync.infrastructure.sink.notion.sync_context_trans import (
    NotionSyncContextTrans,
)
from notes_sync.infrastructure.sink.obsidian.sink import ObsidianSink
from notes_sync.infrastructure.sink.obsidian.sink_trans import ObsidianDiaryTrans
from notes_sync.infrastructure.sink.obsidian.sync_context_source import (
    ObsidianSyncContextSource,
)
from notes_sync.infrastructure.sink.obsidian.sync_context_trans import (
    ObsidianSyncContextTrans,
)
from notes_sync.infrastructure.sources.steps.source import StepsSource
from notes_sync.infrastructure.sources.toggl.mock_source import TogglMockSource
from notes_sync.infrastructure.sources.toggl.source import TogglSource
from notes_sync.infrastructure.sources.toggl.source_trans import TogglSourceTransformer
from notes_sync.models.schema import SinkName, SourceName

logger = logging.getLogger(__name__)


class SourceProvider:
    def __init__(
        self,
        source: DiarySource,
        s_trans: DiarySourceTransformer,
    ):
        self.source = source
        self.s_trans = s_trans


class SinkProvider:
    def __init__(
        self,
        name: SinkName,
        sink: DiarySink,
        s_trans: DiarySinkTransformer,
        ctx_source: DiarySyncContextSource,
        ctx_trans: DiarySyncContextTransformer,
    ):
        self.name = name
        self.sink = sink
        self.s_trans = s_trans
        self.ctx_source = ctx_source
        self.ctx_trans = ctx_trans


def _create_toggl_source() -> SourceProvider:
    """内部工厂：处理具体的 Toggl 构造逻辑"""
    source: DiarySource | None = None
    s = get_settings()
    if s.USE_MOCK_SOURCE:
        source = TogglMockSource()
    else:
        source = TogglSource(api_token=s.TOGGL_API_TOKEN, cache_dir=s.CACHE_DIR)
    return SourceProvider(source, TogglSourceTransformer())


SOURCE_FACTORY = {SourceName.TOGGL: _create_toggl_source}


SINK_FACTORY = {
    SinkName.NOTION: lambda s: SinkProvider(
        SinkName.NOTION,
        NotionSink(s.NOTION_TOKEN, s.NOTION_DATABASE_ID),
        NotionDiaryTrans(),
        NotionSyncContextSource(s.NOTION_TOKEN, s.NOTION_DATABASE_ID),
        NotionSyncContextTrans(),
    ),
    SinkName.OBSIDIAN: lambda s: SinkProvider(
        SinkName.OBSIDIAN,
        ObsidianSink(s.OBSIDIAN_VAULT_PATH),
        ObsidianDiaryTrans(),
        ObsidianSyncContextSource(s.OBSIDIAN_VAULT_PATH),
        ObsidianSyncContextTrans(),
    ),
}


def get_source_provider(source_name: SourceName) -> SourceProvider:
    settings = get_settings()
    factory = SOURCE_FACTORY.get(source_name)

    if not factory:
        raise ValueError(f"Unsupported source type: {source_name}")

    # 如果是 MOCK 模式，打一行日志（可选）
    if settings.USE_MOCK_SOURCE:
        logger.info(f"USING MOCK SOURCE FOR {source_name.value}")

    return factory()


def get_enrichers(source_provider: SourceProvider) -> list[DiaryEnricher]:
    enrichers = [
        StepsEnricher(StepsSource(get_settings().STEPS_DATA_FILE)),
        SleepEnricher(
            source_provider.source,
            source_provider.s_trans,
        ),
        StatisticsEnricher(),
        SummaryEnricher(),
        WeatherEnricher(),
        VisualEnricher(),
    ]
    # 使用 (priority, original_index) 元组作为排序键，确保稳定性
    return [
        e
        for i, e in sorted(
            enumerate(enrichers), key=lambda p: (getattr(p[1], "priority", 100), p[0])
        )
    ]


def get_sink_providers(sink_names: list[SinkName]) -> list[SinkProvider]:
    providers = []

    for s_name in sink_names:
        providers.append(SINK_FACTORY[s_name](get_settings()))

    return providers
