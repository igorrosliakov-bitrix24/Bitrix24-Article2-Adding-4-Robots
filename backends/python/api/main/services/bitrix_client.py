import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models import Bitrix24Account

logger = logging.getLogger(__name__)


class BitrixClientService:
    def __init__(self, bitrix24_account: "Bitrix24Account"):
        self.bitrix24_account = bitrix24_account

    def call_method(self, api_method: str, params: dict[str, Any] | None = None) -> Any:
        logger.info("Calling Bitrix24 API method '%s'", api_method)

        return self.bitrix24_account.client._bitrix_token.call_method(
            api_method=api_method,
            params=params or {},
        )
