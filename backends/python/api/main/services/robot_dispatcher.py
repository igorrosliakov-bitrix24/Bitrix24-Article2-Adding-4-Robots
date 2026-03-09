from .robot_types import RobotExecutionContext, RobotHandlerResult
from ..robot_handlers.format_phone_handler import handle_format_phone
from ..robot_handlers.system_ping_handler import handle_system_ping


class RobotHandlerNotFoundError(ValueError):
    pass


ROBOT_HANDLERS = {
    "format_phone": handle_format_phone,
    "system_ping": handle_system_ping,
}


def dispatch_robot(context: RobotExecutionContext) -> RobotHandlerResult:
    handler = ROBOT_HANDLERS.get(context.robot_code)

    if handler is None:
        raise RobotHandlerNotFoundError(f"Unknown robot handler: {context.robot_code}")

    return handler(context)
