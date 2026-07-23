import logging
from datetime import datetime, timedelta

from notes_sync.core.guard import DefaultDiarySyncGuard
from notes_sync.models.models import (
    Diary,
    DiaryReport,
    DiarySyncContext,
    TimeEntry,
)
from notes_sync.models.schema import SyncAction


def test_sync_guard_basic_update():
    """Guard should return CREATE by default (if no remote_id)."""
    guard = DefaultDiarySyncGuard()
    diary = Diary(date=datetime(2026, 1, 1))
    context = DiarySyncContext()

    decision = guard.evaluate(diary, context)
    assert decision.action == SyncAction.CREATE


def test_sync_guard_overlap_detection(caplog):
    """Guard should detect and log time entry overlaps."""
    guard = DefaultDiarySyncGuard()
    base_time = datetime(2026, 1, 1, 10, 0)

    entries = [
        TimeEntry(start=base_time, end=base_time + timedelta(minutes=30)),
        TimeEntry(
            start=base_time + timedelta(minutes=20),
            end=base_time + timedelta(minutes=40),
        ),
    ]
    diary = Diary(date=base_time, time_entries=entries)
    context = DiarySyncContext()

    with caplog.at_level(logging.WARNING):
        decision = guard.evaluate(diary, context)

    assert decision.action == SyncAction.CREATE
    assert "Overlap detected" in caplog.text


def test_sync_guard_archived_status():
    """Guard should return SKIP when status is archived."""
    guard = DefaultDiarySyncGuard()
    diary = Diary(date=datetime(2026, 1, 1))
    # Must provide remote_id so it doesn't default to CREATE before checking status?
    # Actually, check logic: status check is BEFORE remote_id check?
    # Logic:
    # 22: if context.status == "archived": return SKIP
    # 28: if not context.remote_id: return CREATE
    # So strictly, remote_id is not required for this test if status is checked first.
    # checking code: yes, status check is at line 22, remote_id check at line 28.
    context = DiarySyncContext(status="archived")

    decision = guard.evaluate(diary, context)
    assert decision.action == SyncAction.SKIP


def test_sync_guard_skip_steps():
    """Guard should add 'steps' to skip_fields if context.steps > diary.steps."""
    guard = DefaultDiarySyncGuard()

    # Case 1: context.steps > diary.report.steps -> Expect skip "steps"
    diary = Diary(date=datetime(2026, 1, 1), report=DiaryReport(steps=100))
    # remote_id needed to bypass CREATE check and reach steps check (line 32)
    context = DiarySyncContext(remote_id="existing_id", steps=200)

    decision = guard.evaluate(diary, context)
    assert decision.action == SyncAction.UPDATE
    assert "steps" in decision.skip_fields

    # Case 2: context.steps <= diary.report.steps -> Expect NO skip "steps"
    diary2 = Diary(date=datetime(2026, 1, 1), report=DiaryReport(steps=300))
    context2 = DiarySyncContext(remote_id="existing_id", steps=200)

    decision2 = guard.evaluate(diary2, context2)
    assert "steps" not in decision2.skip_fields
