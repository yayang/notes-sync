from datetime import time

from notes_sync.models.models import TimeEntry


def format_time_range(entry: TimeEntry) -> str:
    """Display a midnight end as 23:59 without changing the recorded interval."""
    start = entry.start.strftime("%H:%M")
    end = entry.end.strftime("%H:%M")
    if entry.end.date() > entry.start.date() and entry.end.time() == time.min:
        end = "23:59"
    return f"{start}-{end}"
