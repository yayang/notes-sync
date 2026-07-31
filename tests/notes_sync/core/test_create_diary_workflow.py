from datetime import date
from types import SimpleNamespace

import pytest

from notes_sync.core.create_diary_workflow import CreateDiaryWorkflow
from notes_sync.models.models import DiarySyncContext
from notes_sync.models.schema import SinkName, SyncAction


class FakeContextSource:
    def fetch_raw_data(self, start: date, end: date):
        return [start]


class FakeContextTrans:
    def __init__(self, context: DiarySyncContext):
        self.context = context

    def to_context(self, raw):
        return {raw[0]: self.context}


class FakeTransformer:
    def transform(self, diary, decision):
        return {
            "date": diary.date.date(),
            "status": diary.status,
            "action": decision.action,
        }


class FakeSink:
    def __init__(self, error: Exception | None = None):
        self.calls = []
        self.error = error

    def sink_data(self, *args):
        if self.error:
            raise self.error
        self.calls.append(args)


def make_provider(context: DiarySyncContext, sink: FakeSink):
    return SimpleNamespace(
        name=SinkName.NOTION,
        ctx_source=FakeContextSource(),
        ctx_trans=FakeContextTrans(context),
        s_trans=FakeTransformer(),
        sink=sink,
    )


def test_creates_only_when_diary_is_missing():
    target_date = date(2026, 7, 20)
    missing_sink = FakeSink()
    existing_sink = FakeSink()
    workflow = CreateDiaryWorkflow(
        [
            make_provider(DiarySyncContext(), missing_sink),
            make_provider(DiarySyncContext(remote_id="existing"), existing_sink),
        ]
    )

    workflow.run(target_date)

    assert len(missing_sink.calls) == 1
    assert missing_sink.calls[0][1]["status"] == "current"
    assert missing_sink.calls[0][-1].action == SyncAction.CREATE
    assert existing_sink.calls == []


def test_reports_sink_failure_for_launchd_retry():
    workflow = CreateDiaryWorkflow(
        [make_provider(DiarySyncContext(), FakeSink(RuntimeError("offline")))]
    )

    with pytest.raises(RuntimeError, match="offline"):
        workflow.run(date(2026, 7, 20))
