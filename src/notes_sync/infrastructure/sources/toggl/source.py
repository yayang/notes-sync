import datetime
import json
import logging
from base64 import b64encode
from pathlib import Path
from typing import Any

import requests

from notes_sync.core.protocols import DiarySource

logger = logging.getLogger(__name__)

# /api/v9/me/time_entries 时，返回的 JSON 只有基础 ID：
# project_id: 只有 ID
# workspace_id: 只有 ID, 暂时不考虑
# task_id: 只有 ID
# 服务应该先下载所有的 Project 和 Client 列表, 并缓存到服务中, 只有当遇到匹配不到的 project 和 workspace 时, 才去重新获取
# /api/v9/workspaces/me/projects
# /api/v9/workspaces/me/clients


# self._projects_cache = {
#     "101": {
#         "name": "Project Alpha",  # 项目本身的名字
#         "client_id": "201"       # 这个项目所属的客户 ID (用来去 _clients_cache 查客户名)
#     }
# }


class TogglSource(DiarySource):
    def __init__(
        self,
        api_token: str,
        cache_dir: Path | None = None,
    ):
        """Initializes the TogglBot with API token and headers."""
        self.api_token = api_token
        self.cache_path = cache_dir / "toggl_metadata.json" if cache_dir else None

        # 缓存 Project 和 Client 元数据: 统一使用 str 类型的 ID
        self._projects_cache: dict[str, dict[str, Any]] = {}
        self._clients_cache: dict[str, str] = {}

        # 尝试从本地持久化缓存加载
        self._load_cache()

        # Toggl requires "api_token:api_token" base64 encoded for Basic Auth
        auth_str = f"{self.api_token}:api_token"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Basic "
            + b64encode(auth_str.encode("ascii")).decode("ascii"),
        }

    def _do_fetch(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> list[Any]:
        """Fetches time entries from Toggl Track API for the given range."""
        start_iso, end_iso = self.__get_utc_range(start_date, end_date)
        url = "https://api.track.toggl.com/api/v9/me/time_entries"
        params = {"start_date": start_iso, "end_date": end_iso}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            raw_entries = response.json()

            # 元数据补全 (Enrichment): 利用缓存和懒加载
            return [self._hydrate_entry(e) for e in raw_entries]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 402:
                logger.error(
                    "Toggl API returned 402 Payment Required. Check your workspace subscription/trial status."
                )
                # We return empty list to prevent crash effectively acting as "no data" if user wants to catch it.
                # Or re-raise with friendly message? User said "catch this".
                # "caught" usually implies handling it. Returning empty list allows workflow to continue (though data is missing).
                # But missing main data source usually makes the rest useless.
                # Let's re-raise a specific known error or just log and return empty if that's safer.
                # Returning empty list is safest "catch".
                return []
            logger.error(f"Failed to fetch Toggl data: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Toggl data: {e}")
            raise

    def fetch_projects(self) -> list[dict[str, Any]]:
        """获取用户在所有工作区下的所有项目，并更新缓存"""
        url = "https://api.track.toggl.com/api/v9/me/projects"
        try:
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            projects = resp.json()
            # 填充缓存
            for p in projects:
                self._projects_cache[str(p["id"])] = {
                    "name": p["name"],
                    "client_id": str(p.get("client_id"))
                    if p.get("client_id") is not None
                    else None,
                }
            self._save_cache()
            return projects
        except Exception as e:
            logger.warning(f"Failed to fetch globally accessible projects: {e}")
            return []

    def fetch_clients(self) -> list[dict[str, Any]]:
        """获取用户在所有工作区下的所有客户，并更新缓存"""
        url = "https://api.track.toggl.com/api/v9/me/clients"
        try:
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            clients = resp.json()
            # 填充缓存
            for c in clients:
                self._clients_cache[str(c["id"])] = c["name"]
            self._save_cache()
            return clients
        except Exception as e:
            logger.warning(f"Failed to fetch globally accessible clients: {e}")
            return []

    def _hydrate_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        """
        补全单条数据: 利用缓存填充名称。
        如果遇到未知的 Project ID, 则触发一次性全局刷新。
        """
        item = entry.copy()
        pid = item.get("project_id")
        if not pid:
            return item

        pid_str = str(pid)

        # 懒加载 (Lazy Loading) 策略：
        # 如果缓存中没有该项目，且该分录确实有项目 ID，则刷新一次全局元数据
        if pid_str not in self._projects_cache:
            logger.info(f"Project ID {pid_str} not in cache. Refreshing metadata...")
            self.fetch_clients()
            self.fetch_projects()

        p_info = self._projects_cache.get(pid_str)
        if p_info:
            item["project_name"] = p_info["name"]
            cid_str = p_info.get("client_id")
            if cid_str:
                item["client_name"] = self._clients_cache.get(cid_str)
            else:
                logger.warning(f"Client ID {cid_str} not found.")
        else:
            logger.warning(f"Project ID {pid_str} not found.")

        return item

    def __get_utc_range(
        self, start_date: datetime.date, end_date: datetime.date
    ) -> tuple[str, str]:
        """Convert local date objects to UTC ISO strings by combining with min/max time."""
        # Convert date to local datetime (assuming local system timezone)
        start_local = datetime.datetime.combine(
            start_date, datetime.time.min
        ).astimezone()
        end_local = datetime.datetime.combine(end_date, datetime.time.max).astimezone()

        start_utc = start_local.astimezone(datetime.timezone.utc)
        end_utc = end_local.astimezone(datetime.timezone.utc)

        # Toggl API expects YYYY-MM-DDTHH:MM:SSZ format
        return start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"), end_utc.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

    def _load_cache(self) -> None:
        """从本地磁盘加载元数据缓存"""
        if not self.cache_path or not self.cache_path.exists():
            return

        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._projects_cache = data.get("projects", {})
                self._clients_cache = data.get("clients", {})
                logger.info(f"Loaded Toggl metadata from cache: {self.cache_path}")
        except Exception as e:
            logger.warning(f"Failed to load Toggl cache: {e}")

    def _save_cache(self) -> None:
        """将当前内存中的元数据缓存写回磁盘"""
        if not self.cache_path:
            return

        try:
            # 确保父目录存在
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"projects": self._projects_cache, "clients": self._clients_cache}
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved Toggl metadata to cache: {self.cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save Toggl cache: {e}")
