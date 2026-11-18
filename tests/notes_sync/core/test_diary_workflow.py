from collections import Counter
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
import requests

from notes_sync.core.builder import SourceProvider
from notes_sync.core.diary_workflow import SyncDiaryWorkflow
from notes_sync.core.guard import DefaultDiarySyncGuard
from notes_sync.core.protocols import RetryableSinkError
from notes_sync.infrastructure.processors.sleep.enricher import SleepEnricher
from notes_sync.infrastructure.sources.toggl.source import TogglSource
from notes_sync.infrastructure.sources.toggl.source_trans import TogglSourceTransformer
from notes_sync.models.models import DiarySyncContext
from notes_sync.models.schema import SinkName, SyncAction


@pytest.mark.parametrize("fail_on_sleep_fetch", [False, True])
def test_toggl_rate_limit_aborts_before_writing(monkeypatch, fail_on_sleep_fetch):
    response = requests.Response()
    response.status_code = 402
    empty = Mock()
    empty.json.return_value = []
    responses = [empty, response] if fail_on_sleep_fetch else [response]
    monkeypatch.setattr(requests, "get", Mock(side_effect=responses))
    monkeypatch.setattr(
        "notes_sync.core.diary_workflow.get_settings",
        lambda: SimpleNamespace(EARLIEST_SYNC_DATE=date.today().isoformat()),
    )
    source = TogglSource(api_token="test_token")
    source.limit = 0
    source.delay = 0
    transformer = TogglSourceTransformer()
    sinks = [Mock(), Mock()]
    workflow = SyncDiaryWorkflow(
        SourceProvider(source, transformer),
        [SleepEnricher(source, transformer)],
        DefaultDiarySyncGuard(),
        sinks,
    )

    with pytest.raises(requests.HTTPError, match="402"):
        workflow.run(days=0)

    for provider in sinks:
        provider.sink.sink_data.assert_not_called()


@pytest.mark.parametrize("retry_succeeds", [True, False])
def test_write_retries_only_the_failed_item(monkeypatch, retry_succeeds):
    end = date.today()
    start = end - timedelta(days=3)
    invalid_day = start + timedelta(days=1)
    transform_failure_day = end - timedelta(days=1)
    monkeypatch.setattr(
        "notes_sync.core.diary_workflow.get_settings",
        lambda: SimpleNamespace(EARLIEST_SYNC_DATE=start.isoformat()),
    )
    wait = Mock()
    monkeypatch.setattr("notes_sync.core.diary_workflow.sleep", wait)

    source = Mock()
    source.fetch_raw_data.return_value = []
    enricher = Mock()
    notion = Mock()
    notion.name = SinkName.NOTION
    notion.ctx_trans.to_context.return_value = {}
    attempts = Counter()

    def transform(diary, decision):
        if diary.date.date() == transform_failure_day:
            raise ValueError("invalid diary")
        return {}

    def write(day, data, context, decision):
        attempts[day] += 1
        if day == start and (attempts[day] == 1 or not retry_succeeds):
            raise RetryableSinkError("connection failed")
        if day == invalid_day:
            raise ValueError("validation failed")

    notion.s_trans.transform.side_effect = transform
    notion.sink.sink_data.side_effect = write
    obsidian = Mock()
    obsidian.name = SinkName.OBSIDIAN
    obsidian.ctx_trans.to_context.return_value = {}
    workflow = SyncDiaryWorkflow(
        SourceProvider(source, TogglSourceTransformer()),
        [enricher],
        DefaultDiarySyncGuard(),
        [notion, obsidian],
    )

    with pytest.raises(RuntimeError) as error:
        workflow.run(days=3)

    assert f"notion/{invalid_day}: validation failed" in str(error.value)
    assert f"notion/{transform_failure_day}: invalid diary" in str(error.value)
    assert (f"notion/{start}: connection failed" in str(error.value)) is not retry_succeeds
    source.fetch_raw_data.assert_called_once_with(start, end)
    enricher.enrich.assert_called_once()
    assert notion.ctx_source.fetch_raw_data.call_args_list == [
        call(start, end), call(start, start)
    ]
    wait.assert_called_once_with(5)
    assert attempts == {start: 2, invalid_day: 1, end: 1}
    assert [call.args[0] for call in obsidian.sink.sink_data.call_args_list] == [
        start, invalid_day, transform_failure_day, end
    ]


@pytest.mark.parametrize("status", ["current", "archived"])
def test_write_retry_respects_new_target_state(monkeypatch, status):
    day = date.today()
    monkeypatch.setattr(
        "notes_sync.core.diary_workflow.get_settings",
        lambda: SimpleNamespace(EARLIEST_SYNC_DATE=day.isoformat()),
    )
    monkeypatch.setattr("notes_sync.core.diary_workflow.sleep", Mock())

    source = Mock()
    source.fetch_raw_data.return_value = []
    provider = Mock()
    provider.name = SinkName.NOTION
    existing = DiarySyncContext(remote_id="created-in-the-meantime", status=status)
    provider.ctx_trans.to_context.side_effect = [{}, {day: existing}]
    provider.sink.sink_data.side_effect = [RetryableSinkError("did not write"), None]
    workflow = SyncDiaryWorkflow(
        SourceProvider(source, TogglSourceTransformer()),
        [],
        DefaultDiarySyncGuard(),
        [provider],
    )

    workflow.run(days=0)

    calls = provider.sink.sink_data.call_args_list
    assert calls[0].args[3].action == SyncAction.CREATE
    if status == "archived":
        assert len(calls) == 1
    else:
        assert calls[1].args[2] == existing
        assert calls[1].args[3].action == SyncAction.UPDATE
