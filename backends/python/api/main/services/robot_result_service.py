import logging
from typing import TYPE_CHECKING, Any

from .bitrix_client import BitrixClientService
from .robot_types import RobotExecutionContext, RobotHandlerResult

if TYPE_CHECKING:
    from ..models import Bitrix24Account

logger = logging.getLogger(__name__)


class RobotResultService:
    def __init__(self, bitrix24_account: "Bitrix24Account | None" = None):
        self.bitrix24_account = bitrix24_account

    def finalize(self, context: RobotExecutionContext, result: RobotHandlerResult) -> dict[str, Any]:
        event_token = self._extract_event_token(context.payload)
        response_payload = {
            "status": result.status,
            "robot_code": context.robot_code,
            "delivery": "local",
            "log_message": result.log_message,
            "return_values": result.return_values,
            "bitrix_event_token_found": bool(event_token),
        }

        if context.is_debug or self.bitrix24_account is None or not event_token:
            logger.info(
                "Robot '%s' finished locally. debug=%s event_token=%s",
                context.robot_code,
                context.is_debug,
                bool(event_token),
            )
            return response_payload

        BitrixClientService(self.bitrix24_account).call_method(
            "bizproc.event.send",
            {
                "EVENT_TOKEN": event_token,
                "RETURN_VALUES": result.return_values,
                "LOG_MESSAGE": result.log_message,
            },
        )

        response_payload["delivery"] = "bitrix24"
        logger.info("Robot '%s' result sent to Bitrix24", context.robot_code)

        return response_payload

    @staticmethod
    def _extract_event_token(payload: dict[str, Any]) -> str | None:
        for key in ("event_token", "EVENT_TOKEN"):
            event_token = payload.get(key)
            if isinstance(event_token, str) and event_token:
                return event_token

        return None
