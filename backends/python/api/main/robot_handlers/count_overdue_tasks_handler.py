from datetime import datetime, timezone

from ..services.crm_timeline_service import CRMTimelineService
from ..services.robot_types import RobotExecutionContext, RobotHandlerResult
from ..services.tasks_overdue_service import OverdueTasksResult, TasksOverdueService


def _debug_result(payload: dict) -> OverdueTasksResult | None:
    debug_current_deal = payload.get("debug_current_deal")
    debug_tasks = payload.get("debug_tasks")

    if not isinstance(debug_current_deal, dict) or not isinstance(debug_tasks, list):
        return None

    responsible_user_id = str(debug_current_deal.get("ASSIGNED_BY_ID", "") or "")
    deal_id = str(debug_current_deal.get("ID", "") or "")
    if not responsible_user_id:
        return OverdueTasksResult(
            responsible_user_id="",
            total_tasks_checked=0,
            overdue_task_count=0,
            current_deal_id=deal_id,
        )

    overdue_task_count = 0
    for task_item in debug_tasks:
        if not isinstance(task_item, dict):
            continue

        if str(task_item.get("RESPONSIBLE_ID", "")) != responsible_user_id:
            continue

        deadline_value = str(task_item.get("DEADLINE", "") or "").strip()
        status_value = str(task_item.get("REAL_STATUS", task_item.get("STATUS", "")) or "").strip()
        if status_value in {"5", "7"}:
            continue
        if not deadline_value:
            continue

        try:
            deadline = datetime.fromisoformat(deadline_value.replace("Z", "+00:00"))
        except ValueError:
            continue

        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        else:
            deadline = deadline.astimezone(timezone.utc)

        if deadline < datetime.now(timezone.utc):
            overdue_task_count += 1

    responsible_tasks_count = len(
        [
            task_item
            for task_item in debug_tasks
            if isinstance(task_item, dict) and str(task_item.get("RESPONSIBLE_ID", "")) == responsible_user_id
        ]
    )

    return OverdueTasksResult(
        responsible_user_id=responsible_user_id,
        total_tasks_checked=responsible_tasks_count,
        overdue_task_count=overdue_task_count,
        current_deal_id=deal_id,
    )


def handle_count_overdue_tasks(context: RobotExecutionContext) -> RobotHandlerResult:
    # Robot 4 orchestration: count overdue tasks and expose the result to BP plus deal timeline.
    if context.bitrix24_account is not None:
        result = TasksOverdueService(context.bitrix24_account).count_from_document(context.payload)
    else:
        result = _debug_result(context.payload)

    if result is None:
        return RobotHandlerResult(
            return_values={
                "responsible_user_id": "",
                "total_tasks_checked": "0",
                "overdue_task_count": "0",
            },
            log_message="count_overdue_tasks could not resolve current deal context",
        )

    timeline_message = (
        f"Просроченные задачи ответственного: {result.overdue_task_count}"
        f" | пользователь: {result.responsible_user_id or '-'}"
        f" | проверено задач: {result.total_tasks_checked}"
    )

    if context.bitrix24_account is not None:
        CRMTimelineService(context.bitrix24_account).add_comment_from_document(
            context.payload,
            timeline_message,
        )

    return RobotHandlerResult(
        return_values={
            "responsible_user_id": result.responsible_user_id,
            "total_tasks_checked": str(result.total_tasks_checked),
            "overdue_task_count": str(result.overdue_task_count),
        },
        log_message=(
            f"count_overdue_tasks overdue_task_count={result.overdue_task_count}, "
            f"responsible_user_id='{result.responsible_user_id}', "
            f"total_tasks_checked={result.total_tasks_checked}"
        ),
    )
