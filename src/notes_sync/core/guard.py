import logging

from notes_sync.core.protocols import DiarySyncGuard
from notes_sync.models.models import Diary, DiarySyncContext
from notes_sync.models.schema import SyncAction, SyncDecision

logger = logging.getLogger(__name__)


class DefaultDiarySyncGuard(DiarySyncGuard):
    def evaluate(self, diary: Diary, context: DiarySyncContext) -> SyncDecision:
        """
        评估日记同步策略
        1. status字段是否是archived
        2. steps字段是否单调递增的
        3. remote_id是否存在, 不存在, 则SyncAction.CREATE
        4. time entry 是否有重叠
        """
        sync_decision = SyncDecision()
        sync_decision.action = SyncAction.UPDATE

        if context.status and context.status.lower() == "archived":
            sync_decision.action = SyncAction.SKIP
            return sync_decision

        self.__check_overlaps(diary)

        if not context.remote_id:
            sync_decision.action = SyncAction.CREATE
            return sync_decision

        if context.steps and context.steps > (diary.report.steps or 0):
            sync_decision.skip_fields = set(["steps"])

        return sync_decision

    def __check_overlaps(self, diary: Diary) -> None:
        last_end = None
        for entry in diary.time_entries:
            if not entry.end:
                continue

            if last_end and entry.start < last_end:
                overlap = (last_end - entry.start).total_seconds()
                if overlap > 60:
                    logger.warning(
                        f"Overlap detected in {diary.date.date()}: "
                        f"Previous end {last_end.time()} overlaps with {entry.start.time()}"
                    )

            last_end = max(last_end, entry.end) if last_end else entry.end
