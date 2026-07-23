from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from notes_sync.infrastructure.sources.toggl.source import TogglSource


def test_toggl_source_utc_range():
    source = TogglSource(api_token="test_token")

    # 设置东八区时间 (UTC+8)
    tz_east8 = timezone(timedelta(hours=8))
    # 东八区 10:00 应当对应 UTC 02:00
    start = datetime(2025, 12, 15, 10, 0, 0, tzinfo=tz_east8)
    # 东八区 20:00 应当对应 UTC 12:00
    end = datetime(2025, 12, 15, 20, 0, 0, tzinfo=tz_east8)

    # Access mangled name
    start_iso, end_iso = source._TogglSource__get_utc_range(start, end)

    # 验证是否正确转换为 UTC 的 ISO 字符串
    # 2025-12-15 00:00:00 (Asia/Shanghai +8) -> 2025-12-14 16:00:00 UTC
    assert start_iso == "2025-12-14T16:00:00Z"
    # End of day 23:59:59 (Asia/Shanghai +8) -> 15:59:59 UTC
    assert end_iso == "2025-12-15T15:59:59Z"


# 拦截了 requests.get 的网络请求，不让它发给真正的 Toggl
# 测试代码是否把 test_token 正确地放进了 HTTP Header 里，以及是否正确处理了返回的 JSON
@patch("requests.get")
def test_toggl_source_fetch_raw_data(mock_get):
    """测试基础的数据抓取功能，验证懒加载缓存行为"""
    # 模拟 API：第一次返回分录 (没有项目 ID)，不需要拿元数据
    mock_resp = MagicMock()
    mock_resp.json.return_value = [{"id": 123}]  # 无项目 ID
    mock_resp.status_code = 200
    mock_resp.ok = True
    mock_get.return_value = mock_resp

    source = TogglSource(api_token="test_token")
    start = datetime(2025, 12, 15, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2025, 12, 15, 23, 59, 59, tzinfo=timezone.utc)

    source.fetch_raw_data(start, end)

    # 验证是否发起了 1 次请求 (因为没有项目 ID，无需拉取元数据)
    assert mock_get.call_count == 1
    assert "time_entries" in mock_get.call_args.args[0]


@patch("requests.get")
def test_toggl_source_enrichment_with_str_normalization(mock_get):
    """验证懒加载模式下的元数据补全逻辑"""
    source = TogglSource(api_token="test_token")

    # 1. 模拟 Time Entries
    mock_entries_resp = MagicMock()
    mock_entries_resp.json.return_value = [
        {"id": 1001, "project_id": 101},
        {"id": "entry_2", "project_id": "proj_102"},
    ]
    mock_entries_resp.ok = True

    # 2. 模拟 Global Clients/Projects
    mock_meta_resp = MagicMock()
    mock_meta_resp.ok = True

    # 获取 Clients 时返回
    mock_clients_data = [{"id": 201, "name": "Work Client"}]
    # 获取 Projects 时返回
    mock_projects_data = [
        {"id": "101", "name": "Project Alpha", "client_id": 201},
        {"id": "proj_102", "name": "Project Beta", "client_id": None},
    ]

    # side_effect 顺序：
    # 1. fetch_raw_data 的 API 调用 (Time entries)
    # 2. 内部 hydrate 第一个分录时由于 PID 101 不在缓存，触发 fetch_clients()
    # 3. 接着触发 fetch_projects()

    # 我们需要能够动态返回 json
    def mock_json_side_effect():
        # 根据请求 URL 返回不同的数据
        call_url = mock_get.call_args.args[0]
        if "time_entries" in call_url:
            return mock_entries_resp.json.return_value
        if "clients" in call_url:
            return mock_clients_data
        if "projects" in call_url:
            return mock_projects_data
        return []

    mock_get.return_value.json.side_effect = mock_json_side_effect
    mock_get.return_value.ok = True

    data = source.fetch_raw_data(
        datetime(2025, 1, 1, tzinfo=timezone.utc),
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    assert len(data) == 2
    # 验证元数据是否正确填充
    assert data[0]["project_name"] == "Project Alpha"
    assert data[0]["client_name"] == "Work Client"
    assert data[1]["project_name"] == "Project Beta"

    # 总请求数应当仍为 3 (Time Entries + Clients + Projects)
    # 第二个分录 proj_102 命中了缓存，不会再发起 API
    assert mock_get.call_count == 3
