import logging
from datetime import date
from pathlib import Path

from notes_sync.core.protocols import DiarySink
from notes_sync.infrastructure.sink.obsidian.mapping import SectionKey
from notes_sync.infrastructure.sink.obsidian.path_resolver import ObsidianPathResolver
from notes_sync.models.models import DiarySyncContext
from notes_sync.models.schema import SyncAction, SyncDecision

logger = logging.getLogger(__name__)


class ObsidianSink(DiarySink[str]):
    """
    Writes diary data to Obsidian markdown files.

    CREATE: Writes full content (YAML + UserSection + Statistics + TimeEntries)
    UPDATE: Preserves existing body after YAML, replaces Statistics + TimeEntries
    """

    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.path_resolver = ObsidianPathResolver(vault_path)

    def sink_data(
        self,
        diary_date: date,
        data: str,
        _: DiarySyncContext,
        sync_decision: SyncDecision,
    ) -> None:
        file_path = self.path_resolver.get_diary_path(diary_date)

        if sync_decision.action == SyncAction.UPDATE:
            self._update_file(file_path, data)
        elif sync_decision.action == SyncAction.CREATE:
            self._create_file(file_path, data)

    def _create_file(self, file_path: Path, content: str) -> None:
        """Create new diary file with full content."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"[ObsidianSink] Created {file_path.name}")

    def _update_file(self, file_path: Path, new_content: str) -> None:
        """
        Update existing file:
        1. Extract YAML frontmatter from NEW content
        2. Preserve EXISTING body after YAML (optionally including header) until STATISTICS
        3. Extract Data Content from NEW content (STATISTICS onwards)
        4. Combine: New YAML + Preserved Body + New Data Content
        """
        existing = file_path.read_text(encoding="utf-8")
        marker_stats = SectionKey.STATISTICS

        new_yaml = self.__extract_yaml_block(new_content)
        existing_body = self.__extract_body_before_stats(existing, marker_stats)
        if not existing_body.strip():
            logger.warning(
                "[ObsidianSink] Skip update for %s: existing body is empty before %s",
                file_path.name,
                marker_stats,
            )
            return

        new_data_content = self.__extract_data_from_stats(new_content, marker_stats)
        updated = self.__merge_sections(new_yaml, existing_body, new_data_content)

        file_path.write_text(updated, encoding="utf-8")
        logger.info(f"[ObsidianSink] Updated {file_path.name}")

    def __extract_yaml_block(self, content: str) -> str:
        """Return YAML frontmatter including the trailing newline."""
        boundary = self.__find_yaml_end(content)
        return content[:boundary]

    def __extract_body_before_stats(self, content: str, marker_stats: str) -> str:
        """Return content after YAML and before STATISTICS."""
        start = self.__find_yaml_end(content)
        end = content.index(marker_stats) if marker_stats in content else len(content)
        return content[start:end]

    def __extract_data_from_stats(self, content: str, marker_stats: str) -> str:
        """Return generated data section starting from STATISTICS."""
        if marker_stats not in content:
            return ""
        return content[content.index(marker_stats) :]

    def __find_yaml_end(self, content: str) -> int:
        """Return the index right after the YAML frontmatter block."""
        if not content.startswith("---\n"):
            return 0

        closing_idx = content.find("\n---", len("---\n"))
        if closing_idx == -1:
            return 0

        after_closing = content.find("\n", closing_idx + 1)
        if after_closing == -1:
            return len(content)

        return after_closing + 1

    def __merge_sections(self, yaml_block: str, body: str, data: str) -> str:
        """Join sections while keeping a safe newline between manual and generated data."""
        updated = f"{yaml_block}{body}"
        if updated and data and not updated.endswith("\n"):
            updated = f"{updated}\n\n"
        return f"{updated}{data}"
