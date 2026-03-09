from ..services.robot_types import RobotExecutionContext, RobotHandlerResult


def handle_system_ping(context: RobotExecutionContext) -> RobotHandlerResult:
    return RobotHandlerResult(
        return_values={
            "message": "robot skeleton is ready",
            "mode": "debug" if context.is_debug else "bitrix24",
        },
        log_message=f"system_ping executed with payload keys: {sorted(context.payload.keys())}",
    )
