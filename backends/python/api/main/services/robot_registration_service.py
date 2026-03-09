import logging
from typing import TYPE_CHECKING, Any

from b24pysdk.error import BitrixAPIError

from .bitrix_client import BitrixClientService
from .robot_registry import get_robot_definitions

if TYPE_CHECKING:
    from ..models import Bitrix24Account

logger = logging.getLogger(__name__)


def _extract_result(response: Any) -> Any:
    if hasattr(response, "result"):
        return response.result

    if isinstance(response, dict):
        return response.get("result", response)

    return response


def _extract_existing_robot_codes(response: Any) -> set[str]:
    result = _extract_result(response)

    if isinstance(result, list):
        robot_items = result
    elif isinstance(result, dict):
        robot_items = result.get("robots") or result.get("items") or []
    else:
        robot_items = []

    codes = set()
    for robot_item in robot_items:
        if isinstance(robot_item, dict):
            robot_code = robot_item.get("CODE")
            if isinstance(robot_code, str) and robot_code:
                codes.add(robot_code)

    return codes


def register_robots_in_bitrix24(
    bitrix24_account: "Bitrix24Account",
    app_base_url: str,
    auth_user_id: int,
) -> list[dict[str, str]]:
    bitrix_client = BitrixClientService(bitrix24_account)
    existing_robot_codes = _extract_existing_robot_codes(
        bitrix_client.call_method("bizproc.robot.list")
    )

    registration_results = []

    for robot_definition in get_robot_definitions():
        payload = robot_definition.to_registration_payload(app_base_url, auth_user_id)

        try:
            if robot_definition.code in existing_robot_codes:
                logger.info(
                    "Robot '%s' already exists in Bitrix24, deleting before re-adding",
                    robot_definition.code,
                )
                bitrix_client.call_method(
                    "bizproc.robot.delete",
                    {"CODE": robot_definition.code},
                )
                action = "recreated"
            else:
                action = "added"

            bitrix_client.call_method("bizproc.robot.add", payload)
        except BitrixAPIError as error:
            error_message = getattr(error, "message", str(error))
            error_message_lower = error_message.lower()

            if "already installed" in error_message_lower:
                logger.info(
                    "Robot '%s' still exists in Bitrix24, deleting and retrying add",
                    robot_definition.code,
                )
                bitrix_client.call_method(
                    "bizproc.robot.delete",
                    {"CODE": robot_definition.code},
                )
                bitrix_client.call_method("bizproc.robot.add", payload)
                action = "recreated"
            elif "not found" in error_message_lower:
                logger.info(
                    "Robot '%s' was not found during delete/update flow, retrying add",
                    robot_definition.code,
                )
                bitrix_client.call_method("bizproc.robot.add", payload)
                action = "added"
            else:
                raise

        registration_results.append({
            "code": robot_definition.code,
            "action": action,
        })

    return registration_results
