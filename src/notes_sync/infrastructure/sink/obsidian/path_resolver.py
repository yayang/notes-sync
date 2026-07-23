"""
Path resolution for Obsidian diary files.

Sub-path structure:
    70_Journal/{YYYY}/{MM}/{YYYY-MM-DD}.md
"""

from datetime import date
from pathlib import Path


class ObsidianPathResolver:
    """Resolves file paths for Obsidian diary entries."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)

    def get_diary_path(self, diary_date: date) -> Path:
        """Calculate the full path for a diary file based on date."""
        year = str(diary_date.year)
        month = f"{diary_date.month:02d}"
        filename = f"{diary_date.isoformat()}.md"

        return self.vault_path / "70_Journal" / year / month / filename

    def exists(self, diary_date: date) -> bool:
        """Check if the diary file exists for the given date."""
        return self.get_diary_path(diary_date).exists()
