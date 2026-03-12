from .robot_types import RobotExecutionContext, RobotHandlerResult
from ..robot_handlers.count_overdue_tasks_handler import handle_count_overdue_tasks
from ..robot_handlers.format_phone_handler import handle_format_phone
from ..robot_handlers.normalize_full_name_handler import handle_normalize_full_name
from ..robot_handlers.sum_client_deals_handler import handle_sum_client_deals


class RobotHandlerNotFoundError(ValueError):
    pass

ROBOT_HANDLERS = {
    # Robot 1 handler entrypoint.
    "format_phone": handle_format_phone,
    # Robot 2 handler entrypoint.
    "normalize_full_name": handle_normalize_full_name,
    # Robot 3 handler entrypoint.
    "sum_client_deals": handle_sum_client_deals,
    # Robot 4 handler entrypoint.
    "count_overdue_tasks": handle_count_overdue_tasks,
}


def dispatch_robot(context: RobotExecutionContext) -> RobotHandlerResult:
    handler = ROBOT_HANDLERS.get(context.robot_code)

    if handler is None:
        raise RobotHandlerNotFoundError(f"Unknown robot handler: {context.robot_code}")

    return handler(context)
