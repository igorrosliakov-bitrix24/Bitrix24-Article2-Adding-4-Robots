from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..models import Bitrix24Account

JSONDict = dict[str, Any]


@dataclass(frozen=True)
class RobotExecutionContext:
    robot_code: str
    payload: JSONDict
    bitrix24_account: "Bitrix24Account | None" = None
    is_debug: bool = False


@dataclass(frozen=True)
class RobotHandlerResult:
    return_values: JSONDict = field(default_factory=dict)
    log_message: str = ""
    status: str = "success"


RobotHandler = Callable[[RobotExecutionContext], RobotHandlerResult]
