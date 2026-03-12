from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from .bitrix_client import BitrixClientService
from .crm_phone_sync_service import CRMPhoneSyncService

if TYPE_CHECKING:
    from ..models import Bitrix24Account


@dataclass(frozen=True)
class OverdueTasksResult:
    responsible_user_id: str
    total_tasks_checked: int
    overdue_task_count: int
    current_deal_id: str


class TasksOverdueService:
    # Robot 4 service: count overdue tasks for the responsible user of the current deal.
    def __init__(self, bitrix24_account: "Bitrix24Account"):
        self.bitrix_client = BitrixClientService(bitrix24_account)

    def count_from_document(self, payload: dict[str, Any]) -> OverdueTasksResult | None:
        document_token = CRMPhoneSyncService._extract_document_token(payload)
        if not isinstance(document_token, str) or not document_token.startswith("DEAL_"):
            return None

        deal_id = int(document_token.split("_", 1)[1])
        return self._count_for_deal(deal_id)

    def _count_for_deal(self, deal_id: int) -> OverdueTasksResult | None:
        deal_response = self.bitrix_client.call_method("crm.deal.get", {"id": deal_id})
        current_deal = self._extract_result(deal_response)
        if not isinstance(current_deal, dict):
            return None

        responsible_user_id = CRMPhoneSyncService._normalize_entity_id(current_deal.get("ASSIGNED_BY_ID"))
        if responsible_user_id is None:
            return OverdueTasksResult(
                responsible_user_id="",
                total_tasks_checked=0,
                overdue_task_count=0,
                current_deal_id=str(deal_id),
            )

        tasks = self._list_tasks_for_user(responsible_user_id)
        overdue_task_count = sum(1 for task in tasks if _is_task_overdue(task))

        return OverdueTasksResult(
            responsible_user_id=str(responsible_user_id),
            total_tasks_checked=len(tasks),
            overdue_task_count=overdue_task_count,
            current_deal_id=str(deal_id),
        )

    def _list_tasks_for_user(self, responsible_user_id: int) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        page: int = 1

        while True:
            response = self.bitrix_client.call_method(
                "tasks.task.list",
                {
                    "filter": {
                        "RESPONSIBLE_ID": responsible_user_id,
                    },
                    "select": ["ID", "TITLE", "DEADLINE", "REAL_STATUS", "STATUS"],
                    "page": page,
                },
            )
            batch_items, has_more = self._extract_tasks_and_has_more(response)
            tasks.extend(batch_items)
            if not has_more:
                break
            page += 1

        return tasks

    @staticmethod
    def _extract_result(response: Any) -> Any:
        if hasattr(response, "result"):
            return response.result

        if isinstance(response, dict):
            return response.get("result", response)

        return response

    @staticmethod
    def _extract_tasks_and_has_more(response: Any) -> tuple[list[dict[str, Any]], bool]:
        result = TasksOverdueService._extract_result(response)
        next_page = None

        if hasattr(response, "next"):
            next_page = getattr(response, "next")
        elif isinstance(response, dict):
            next_page = response.get("next")

        if isinstance(result, dict):
            raw_tasks = result.get("tasks") or result.get("items") or result.get("result") or []
        elif isinstance(result, list):
            raw_tasks = result
        else:
            raw_tasks = []

        tasks: list[dict[str, Any]] = []
        for task_item in raw_tasks:
            if isinstance(task_item, dict):
                if "task" in task_item and isinstance(task_item["task"], dict):
                    tasks.append(task_item["task"])
                else:
                    tasks.append(task_item)

        return tasks, bool(next_page)


def _is_task_overdue(task: dict[str, Any]) -> bool:
    deadline_value = _read_task_field(task, "deadline", "DEADLINE")
    if not isinstance(deadline_value, str) or not deadline_value.strip():
        return False

    deadline = _parse_datetime(deadline_value)
    if deadline is None:
        return False

    status_value = str(
        _read_task_field(task, "realStatus", "REAL_STATUS", "status", "STATUS") or ""
    ).strip()
    if status_value in {"5", "7"}:
        return False

    return deadline < datetime.now(timezone.utc)


def _read_task_field(task: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in task:
            return task[key]
    return None


def _parse_datetime(raw_value: str) -> datetime | None:
    normalized = raw_value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)
