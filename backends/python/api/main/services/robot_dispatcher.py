from .robot_types import RobotExecutionContext, RobotHandlerResult
from ..robot_handlers.format_phone_handler import handle_format_phone


class RobotHandlerNotFoundError(ValueError):
    pass


ROBOT_HANDLERS = {
    "format_phone": handle_format_phone,
}


def dispatch_robot(context: RobotExecutionContext) -> RobotHandlerResult:
    handler = ROBOT_HANDLERS.get(context.robot_code)

    if handler is None:
        raise RobotHandlerNotFoundError(f"Unknown robot handler: {context.robot_code}")

    return handler(context)
