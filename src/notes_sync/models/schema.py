from enum import StrEnum
from typing import Any, ItemsView


class SourceName(StrEnum):
    TOGGL = "toggl"


class SinkName(StrEnum):
    NOTION = "notion"
    OBSIDIAN = "obsidian"


class SyncAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"


class KVProxy:
    def __init__(self, data: dict[str, Any], skip_keys: set[str]):
        self._data = data
        self._skip_keys = skip_keys

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if value is not None and key not in self._skip_keys:
            self._data[key] = value

    def items(self) -> ItemsView[str, Any]:
        return self._data.items()

    def unwrap(self) -> dict[str, Any]:
        return self._data

    def __repr__(self) -> str:
        return f"KVProxy(fields={list(self._data.keys())}, skipped={self._skip_keys})"


class SyncDecision:
    def __init__(
        self, action: SyncAction = SyncAction.SKIP, skip_fields: set[str] | None = None
    ):
        self.action = action
        self.skip_fields = skip_fields or set()
