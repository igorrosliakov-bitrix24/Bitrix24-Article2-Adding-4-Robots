from b24pysdk.utils.types import JSONDict

from ..utils.bitrix_account_factory import resolve_bitrix24_account
from .robot_dispatcher import dispatch_robot
from .robot_result_service import RobotResultService
from .robot_types import RobotExecutionContext


class RobotExecutionService:
    @staticmethod
    def execute(robot_code: str, payload: JSONDict, is_debug: bool = False) -> dict:
        # Shared execution pipeline for all robots:
        # Robot 1 - format_phone
        # Robot 2 - normalize_full_name
        # Robot 3 - sum_client_deals
        # Robot 4 - count_overdue_tasks
        bitrix24_account = None if is_debug else resolve_bitrix24_account(payload)
        context = RobotExecutionContext(
            robot_code=robot_code,
            payload=payload,
            bitrix24_account=bitrix24_account,
            is_debug=is_debug,
        )
        handler_result = dispatch_robot(context)
        return RobotResultService(bitrix24_account).finalize(context, handler_result)
