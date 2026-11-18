import json
from datetime import date, datetime
from unittest.mock import patch

import httpx
import pytest

from notes_sync.core.protocols import RetryableSinkError
from notes_sync.infrastructure.sink.notion.mapping import DiaryKey
from notes_sync.infrastructure.sink.notion.sink import NotionSink
from notes_sync.infrastructure.sink.notion.sink_trans import NotionDiaryTrans
from notes_sync.models.models import (
    CategoryReport,
    Diary,
    DiaryReport,
    DiarySyncContext,
    SleepReport,
    SleepStatus,
    WeatherReport,
    WeatherStatus,
)
from notes_sync.models.schema import SinkName, SyncAction, SyncDecision


class TestNotionDiaryTrans:
    def test_transform_with_sleep_report(self):
        trans = NotionDiaryTrans()
        diary = Diary(
            date=datetime(2026, 1, 1),
            status=None,
            report=DiaryReport(
                sleep=SleepReport(
                    bed_time="23:30",
                    bed_status=SleepStatus.ON_TIME,
                    wake_time="07:00",
                    wake_status=SleepStatus.ON_TIME,
                    linger_time="15",
                )
            ),
        )
        # transform now returns formatted_data required by sink
        props = trans.transform(diary, SyncDecision(action=SyncAction.UPDATE))

        assert props[DiaryKey.STATUS] == "current"
        assert props[DiaryKey.BED_TIME_PREV] == "23:30"
        assert props[DiaryKey.BED_STATUS_PREV] == "on_time"
        assert props[DiaryKey.GETUP_TIME] == "07:00"
        assert props[DiaryKey.GETUP_STATUS] == "on_time"
        assert props[DiaryKey.LINGER_MINUTES] == "15"

    def test_transform_with_steps_override(self):
        """Verify context.steps takes precedence if larger."""
        trans = NotionDiaryTrans()
        diary = Diary(
            date=datetime(2026, 1, 1),
            report=DiaryReport(steps=1000),
        )
        # Context says steps should be 2000
        diary.sync_contexts[SinkName.NOTION] = DiarySyncContext(steps=2000)

        props = trans.transform(
            diary,
            SyncDecision(action=SyncAction.UPDATE, skip_fields=[DiaryKey.STEPS.value]),
        )
        assert DiaryKey.STEPS not in props

    def test_transform_with_weather(self):
        trans = NotionDiaryTrans()
        diary = Diary(
            date=datetime(2026, 1, 1),
            report=DiaryReport(
                weather=WeatherReport(
                    temp_high=25,
                    temp_low=15,
                    weather=WeatherStatus.SUNNY,
                    air_quality=50,
                )
            ),
        )
        props = trans.transform(diary, SyncDecision(action=SyncAction.UPDATE))

        assert props[DiaryKey.TEMP_HIGH] == 25
        assert props[DiaryKey.TEMP_LOW] == 15
        assert props[DiaryKey.WEATHER] == "Sunny"

    def test_transform_full_properties(self):
        """Verify all keys are present in Notion properties."""
        trans = NotionDiaryTrans()
        diary = Diary(
            date=datetime(2026, 1, 1),
            report=DiaryReport(
                time={
                    "Focus": CategoryReport(total_seconds=3600),
                    "Play": CategoryReport(total_seconds=7200),
                },
                weather=WeatherReport(
                    temp_high=30,
                    temp_low=20,
                    weather=WeatherStatus.SUNNY,
                    air_quality=50,
                    pm25=15,
                ),
            ),
        )
        props = trans.transform(diary, SyncDecision(action=SyncAction.UPDATE))

        assert props[DiaryKey.FOCUS_HOURS] == 1.0
        assert props[DiaryKey.PLAY_HOURS] == 2.0
        assert (
            props[DiaryKey.ROUTINE_HOURS] == 0.0
        )  # Default if key missing or mapped from Routine
        assert props[DiaryKey.PM25] == 15
        assert props[DiaryKey.TEMP_HIGH] == 30


class TestNotionSink:
    def test_writes_long_rich_text_without_losing_content(self, monkeypatch):
        content = "汉" * 1999 + "😀\n" + "条目" * 600

        def accept_valid_payload(request):
            properties = json.loads(request.content)["properties"]
            entries = properties[DiaryKey.TIME_ENTRIES]["rich_text"]
            chunks = [entry["text"]["content"] for entry in entries]
            assert len(chunks) > 1
            assert max(len(chunk.encode("utf-16-le")) // 2 for chunk in chunks) <= 2000
            assert "".join(chunks) == content
            assert properties[DiaryKey.BED_TIME_PREV]["rich_text"] == [
                {"text": {"content": ""}}
            ]
            return httpx.Response(200, json={})

        self._mock_http(monkeypatch, accept_valid_payload)
        self._update_time_entries(content)

    def test_rejects_oversize_rich_text_before_sending(self, monkeypatch):
        def unexpected_request(request):
            pytest.fail(f"Unexpected {request.method} request")

        self._mock_http(monkeypatch, unexpected_request)
        with pytest.raises(ValueError, match="exceeds 100 elements"):
            self._update_time_entries("x" * 200001)

    @pytest.mark.parametrize(
        ("status", "headers", "body", "retryable"),
        [
            (400, {}, {"code": "validation_error"}, False),
            (429, {"Retry-After": "5"}, {"code": "rate_limited"}, True),
            (429, {"Retry-After": "6"}, {"code": "rate_limited"}, False),
            (429, {}, {"code": "rate_limited"}, False),
            (429, {"Retry-After": "unknown"}, {"code": "rate_limited"}, False),
            (
                429,
                {"Retry-After": "5"},
                {"additional_data": {"rate_limit_reason": "public_api_request_blocked"}},
                False,
            ),
            (503, {}, {}, False),
        ],
    )
    def test_classifies_http_write_failures(
        self, monkeypatch, status, headers, body, retryable
    ):
        def reject(request):
            return httpx.Response(status, headers=headers, json=body)

        self._mock_http(monkeypatch, reject)
        with pytest.raises(RuntimeError, match=f"Notion API failed: {status}") as raised:
            self._update_time_entries("work")

        assert isinstance(raised.value, RetryableSinkError) is retryable

    @pytest.mark.parametrize(
        ("failure", "expected"),
        [
            (httpx.ConnectError, RetryableSinkError),
            (httpx.ConnectTimeout, RetryableSinkError),
            (httpx.ReadTimeout, httpx.ReadTimeout),
            (httpx.WriteTimeout, httpx.WriteTimeout),
        ],
    )
    def test_classifies_connection_failures(self, monkeypatch, failure, expected):
        def fail(request):
            raise failure("Network failure", request=request)

        self._mock_http(monkeypatch, fail)
        with pytest.raises(expected, match="Network failure"):
            self._update_time_entries("work")

    @pytest.mark.parametrize(("delay", "rejections"), [(6, 1), (5, 2)])
    def test_cools_down_later_dates_after_rate_limit(self, monkeypatch, delay, rejections):
        now = 100.0
        calls = []
        monkeypatch.setattr(
            "notes_sync.infrastructure.sink.notion.sink.monotonic", lambda: now
        )

        def respond(request):
            calls.append(request.url.path)
            if len(calls) <= rejections:
                return httpx.Response(429, headers={"Retry-After": str(delay)}, json={})
            return httpx.Response(200, json={})

        self._mock_http(monkeypatch, respond)
        sink = NotionSink(token="test_token", db_id="test_db_id")
        first_date = date(2026, 11, 15)
        next_date = date(2026, 11, 16)
        if rejections == 2:
            with pytest.raises(RetryableSinkError):
                self._update_time_entries("work", sink, first_date)
            now += delay
        with pytest.raises(RuntimeError, match="Notion API failed: 429"):
            self._update_time_entries("work", sink, first_date)
        now += delay - 1
        with pytest.raises(RuntimeError, match="Notion write deferred"):
            self._update_time_entries("work", sink, next_date)
        assert len(calls) == rejections

        now += 1
        self._update_time_entries("work", sink, next_date)
        assert len(calls) == rejections + 1

    @pytest.mark.parametrize(
        ("headers", "body"),
        [
            ({}, {}),
            ({"Retry-After": "unknown"}, {}),
            (
                {"Retry-After": "5"},
                {"additional_data": {"rate_limit_reason": "public_api_request_blocked"}},
            ),
        ],
    )
    def test_defers_indefinite_rate_limit_for_the_run(self, monkeypatch, headers, body):
        now = 100.0
        calls = []
        monkeypatch.setattr(
            "notes_sync.infrastructure.sink.notion.sink.monotonic", lambda: now
        )

        def reject(request):
            calls.append(request.url.path)
            return httpx.Response(429, headers=headers, json=body)

        self._mock_http(monkeypatch, reject)
        sink = NotionSink(token="test_token", db_id="test_db_id")
        with pytest.raises(RuntimeError, match="Notion API failed: 429"):
            self._update_time_entries("work", sink)
        now += 3600
        with pytest.raises(RuntimeError, match="Notion write deferred"):
            self._update_time_entries("work", sink, date(2026, 11, 16))
        assert len(calls) == 1

    def _mock_http(self, monkeypatch, handler):
        client = httpx.Client
        transport = httpx.MockTransport(handler)
        monkeypatch.setattr(httpx, "Client", lambda: client(transport=transport))

    def _update_time_entries(self, content, sink=None, diary_date=date(2026, 11, 15)):
        if sink is None:
            sink = NotionSink(token="test_token", db_id="test_db_id")
        sink.sink_data(
            diary_date,
            {DiaryKey.TIME_ENTRIES: content, DiaryKey.BED_TIME_PREV: ""},
            DiarySyncContext(remote_id=f"page_{diary_date.isoformat()}"),
            SyncDecision(action=SyncAction.UPDATE),
        )

    def test_sink_data_creates_new_page(self):
        """When remote_id is None in data tuple, should call POST."""
        sink = NotionSink(token="test_token", db_id="test_db_id")
        today = date(2026, 1, 1)

        # sink_data(diary_date, data, context, sync_decision)
        context = DiarySyncContext()
        decision = SyncDecision(action=SyncAction.CREATE)
        formatted_props = {DiaryKey.STEPS: 5000}

        with patch.object(sink, "_NotionSink__send_request") as mock_request:
            mock_request.return_value = {"id": "new_page_id"}
            sink.sink_data(today, formatted_props, context, decision)

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"  # Method
            assert "pages" in call_args[0][1]  # URL contains /pages

    def test_sink_data_updates_existing_page(self):
        """When remote_id is present in data tuple, should call PATCH."""
        sink = NotionSink(token="test_token", db_id="test_db_id")
        today = date(2026, 1, 1)

        # Data: props dict
        props = {DiaryKey.STEPS: 5000}

        # Context has remote_id for UPDATE
        context = DiarySyncContext(remote_id="existing_page_id")
        decision = SyncDecision(action=SyncAction.UPDATE)

        with patch.object(sink, "_NotionSink__send_request") as mock_request:
            mock_request.return_value = {"id": "existing_page_id"}
            sink.sink_data(today, props, context, decision)

            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "PATCH"  # Method
            assert "existing_page_id" in call_args[0][1]  # URL contains page_id

    def test_build_notion_properties_number(self):
        """Verify number properties are formatted correctly."""
        sink = NotionSink(token="test_token", db_id="test_db_id")

        props = {DiaryKey.STEPS: 5000, DiaryKey.FOCUS_HOURS: 2.5}
        result = sink._NotionSink__build_notion_properties(None, props)

        assert result[DiaryKey.STEPS] == {"number": 5000}
        assert result[DiaryKey.FOCUS_HOURS] == {"number": 2.5}

    def test_build_notion_properties_string(self):
        """Verify string properties are formatted correctly."""
        sink = NotionSink(token="test_token", db_id="test_db_id")

        props = {DiaryKey.BED_TIME_PREV: "23:30"}
        result = sink._NotionSink__build_notion_properties(None, props)

        assert result[DiaryKey.BED_TIME_PREV] == {
            "rich_text": [{"text": {"content": "23:30"}}]
        }

    def test_build_notion_properties_select(self):
        """Verify select properties are formatted correctly."""
        sink = NotionSink(token="test_token", db_id="test_db_id")

        props = {
            DiaryKey.WEATHER: "Sunny",
            DiaryKey.BED_STATUS_PREV: "on_time",
        }
        result = sink._NotionSink__build_notion_properties(None, props)

        assert result[DiaryKey.WEATHER] == {"select": {"name": "Sunny"}}
        assert result[DiaryKey.BED_STATUS_PREV] == {"select": {"name": "on_time"}}

    def test_build_notion_properties_with_date(self):
        """Verify date is added for create operations."""
        sink = NotionSink(token="test_token", db_id="test_db_id")
        today = date(2026, 1, 1)

        result = sink._NotionSink__build_notion_properties(today, {})

        # Name uses title with date mention
        assert result[DiaryKey.NAME] == {
            "title": [
                {
                    "type": "mention",
                    "mention": {"type": "date", "date": {"start": "2026-01-01"}},
                }
            ]
        }

    def test_sink_data_with_icon(self):
        """Verify icon is extracted from props and moved to payload root."""
        sink = NotionSink(token="t", db_id="d")
        today = date(2026, 1, 1)
        props = {DiaryKey.STEPS: 100, DiaryKey.ICON: "http://icon.url"}

        # Test Create (remote_id is None)
        with patch.object(sink, "_NotionSink__send_request") as mock_request:
            mock_request.return_value = {}
            sink._create_page(today, props)
            call_args = mock_request.call_args[0]
            body = call_args[2]  # 3rd arg is body
            assert body["icon"] == {
                "type": "external",
                "external": {"url": "http://icon.url"},
            }
            # Ensure icon is NOT in properties
            assert DiaryKey.ICON not in body["properties"]

        # Test Update (remote_id provided)
        with patch.object(sink, "_NotionSink__send_request") as mock_request:
            mock_request.return_value = {}
            sink._update_page("page_id", props)
            call_args = mock_request.call_args[0]
            body = call_args[2]
            assert body["icon"] == {
                "type": "external",
                "external": {"url": "http://icon.url"},
            }
            assert DiaryKey.ICON not in body["properties"]
