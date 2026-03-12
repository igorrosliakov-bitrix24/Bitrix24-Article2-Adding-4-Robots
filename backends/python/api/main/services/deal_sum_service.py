from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, TYPE_CHECKING

from .bitrix_client import BitrixClientService
from .crm_phone_sync_service import CRMPhoneSyncService

if TYPE_CHECKING:
    from ..models import Bitrix24Account


@dataclass(frozen=True)
class DealSumResult:
    deal_count: int
    total_amount: str
    currency_id: str
    client_entity_type: str
    client_entity_id: str
    current_deal_id: str


class DealSumService:
    # Robot 3 service: find the current deal client and sum all client deals.
    def __init__(self, bitrix24_account: "Bitrix24Account"):
        self.bitrix_client = BitrixClientService(bitrix24_account)

    def summarize_from_document(self, payload: dict[str, Any]) -> DealSumResult | None:
        document_token = CRMPhoneSyncService._extract_document_token(payload)
        if not isinstance(document_token, str) or not document_token.startswith("DEAL_"):
            return None

        deal_id = int(document_token.split("_", 1)[1])
        return self._summarize_for_deal(deal_id)

    def _summarize_for_deal(self, deal_id: int) -> DealSumResult | None:
        deal_response = self.bitrix_client.call_method("crm.deal.get", {"id": deal_id})
        current_deal = self._extract_result(deal_response)
        if not isinstance(current_deal, dict):
            return None

        company_id = CRMPhoneSyncService._normalize_entity_id(current_deal.get("COMPANY_ID"))
        contact_id = CRMPhoneSyncService._normalize_entity_id(current_deal.get("CONTACT_ID"))

        if company_id is not None:
            client_entity_type = "company"
            filter_field = "COMPANY_ID"
            client_entity_id = company_id
        elif contact_id is not None:
            client_entity_type = "contact"
            filter_field = "CONTACT_ID"
            client_entity_id = contact_id
        else:
            return DealSumResult(
                deal_count=0,
                total_amount="0.00",
                currency_id=str(current_deal.get("CURRENCY_ID", "") or ""),
                client_entity_type="",
                client_entity_id="",
                current_deal_id=str(deal_id),
            )

        deals = self._list_deals({filter_field: client_entity_id})
        total_amount = Decimal("0.00")

        for deal_item in deals:
            if not isinstance(deal_item, dict):
                continue
            total_amount += _to_decimal(deal_item.get("OPPORTUNITY"))

        currency_id = str(current_deal.get("CURRENCY_ID", "") or "")

        return DealSumResult(
            deal_count=len([deal_item for deal_item in deals if isinstance(deal_item, dict)]),
            total_amount=f"{total_amount.quantize(Decimal('0.01'))}",
            currency_id=currency_id,
            client_entity_type=client_entity_type,
            client_entity_id=str(client_entity_id),
            current_deal_id=str(deal_id),
        )

    def _list_deals(self, filter_values: dict[str, Any]) -> list[dict[str, Any]]:
        deals: list[dict[str, Any]] = []
        start: int | None = 0

        while start is not None:
            params = {
                "filter": filter_values,
                "select": ["ID", "TITLE", "OPPORTUNITY", "COMPANY_ID", "CONTACT_ID"],
                "start": start,
            }
            response = self.bitrix_client.call_method("crm.deal.list", params)
            batch_items, next_start = self._extract_list_and_next(response)
            deals.extend(item for item in batch_items if isinstance(item, dict))
            start = next_start

        return deals

    @staticmethod
    def _extract_result(response: Any) -> Any:
        if hasattr(response, "result"):
            return response.result

        if isinstance(response, dict):
            return response.get("result", response)

        return response

    @staticmethod
    def _extract_list_and_next(response: Any) -> tuple[list[Any], int | None]:
        if hasattr(response, "result"):
            result = response.result
            next_start = getattr(response, "next", None)
            if isinstance(result, list):
                return result, next_start
            if isinstance(result, dict):
                items = result.get("items") or result.get("result") or []
                return items if isinstance(items, list) else [], next_start

        if isinstance(response, dict):
            result = response.get("result", response)
            next_start = response.get("next")
            if isinstance(result, list):
                return result, next_start if isinstance(next_start, int) else None
            if isinstance(result, dict):
                items = result.get("items") or result.get("result") or []
                return items if isinstance(items, list) else [], next_start if isinstance(next_start, int) else None

        return [], None


def _to_decimal(raw_value: Any) -> Decimal:
    try:
        return Decimal(str(raw_value or 0))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")
