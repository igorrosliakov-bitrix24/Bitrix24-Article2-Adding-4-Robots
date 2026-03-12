from typing import TYPE_CHECKING

from .bitrix_client import BitrixClientService
from .crm_phone_sync_service import CRMPhoneSyncService

if TYPE_CHECKING:
    from ..models import Bitrix24Account


class CRMTimelineService:
    # Shared helper for robots 3 and 4: write a visible result into the current deal timeline.
    def __init__(self, bitrix24_account: "Bitrix24Account"):
        self.bitrix_client = BitrixClientService(bitrix24_account)

    def add_comment_from_document(self, payload: dict, comment: str) -> bool:
        document_token = CRMPhoneSyncService._extract_document_token(payload)
        if not isinstance(document_token, str) or not document_token.startswith("DEAL_"):
            return False

        deal_id = int(document_token.split("_", 1)[1])
        self.add_deal_comment(deal_id, comment)
        return True

    def add_deal_comment(self, deal_id: int, comment: str) -> None:
        self.bitrix_client.call_method(
            "crm.timeline.comment.add",
            {
                "fields": {
                    "ENTITY_ID": deal_id,
                    "ENTITY_TYPE": "deal",
                    "COMMENT": comment,
                },
            },
        )
