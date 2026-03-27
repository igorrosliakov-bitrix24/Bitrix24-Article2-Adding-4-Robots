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


class CurrencyConversionError(ValueError):
    pass


class DealSumService:
    # Robot 3 service: find the current deal client and sum all client deals.
    TARGET_CURRENCY_ID = "USD"

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
                currency_id=self.TARGET_CURRENCY_ID,
                client_entity_type="",
                client_entity_id="",
                current_deal_id=str(deal_id),
            )

        deals = self._list_deals({filter_field: client_entity_id})
        currency_rates = self._get_currency_rates({
            self.TARGET_CURRENCY_ID,
            *[
                str(deal_item.get("CURRENCY_ID", "") or "").upper()
                for deal_item in deals
                if isinstance(deal_item, dict)
            ],
        })
        total_amount = Decimal("0.00")

        for deal_item in deals:
            if not isinstance(deal_item, dict):
                continue
            total_amount += self._convert_amount_to_target(
                amount=_to_decimal(deal_item.get("OPPORTUNITY")),
                source_currency_id=str(deal_item.get("CURRENCY_ID", "") or "").upper(),
                currency_rates=currency_rates,
            )

        return DealSumResult(
            deal_count=len([deal_item for deal_item in deals if isinstance(deal_item, dict)]),
            total_amount=f"{total_amount.quantize(Decimal('0.01'))}",
            currency_id=self.TARGET_CURRENCY_ID,
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
                "select": ["ID", "TITLE", "OPPORTUNITY", "CURRENCY_ID", "COMPANY_ID", "CONTACT_ID"],
                "start": start,
            }
            response = self.bitrix_client.call_method("crm.deal.list", params)
            batch_items, next_start = self._extract_list_and_next(response)
            deals.extend(item for item in batch_items if isinstance(item, dict))
            start = next_start

        return deals

    def _convert_amount_to_target(
        self,
        amount: Decimal,
        source_currency_id: str,
        currency_rates: dict[str, Decimal],
    ) -> Decimal:
        source_currency_id = source_currency_id.upper()
        if not source_currency_id:
            raise CurrencyConversionError("Deal currency is empty, USD conversion is not possible")

        if source_currency_id == self.TARGET_CURRENCY_ID or amount == Decimal("0.00"):
            return amount

        source_rate = currency_rates[source_currency_id]
        target_rate = currency_rates[self.TARGET_CURRENCY_ID]
        return amount * source_rate / target_rate

    def _get_currency_rates(self, currency_ids: set[str]) -> dict[str, Decimal]:
        normalized_currency_ids = {currency_id.upper() for currency_id in currency_ids if currency_id}
        if not normalized_currency_ids:
            return {}

        response = self.bitrix_client.call_method("crm.currency.list", {})
        currencies = self._extract_currency_list(response)
        rates: dict[str, Decimal] = {}

        for currency_item in currencies:
            currency_code = str(
                currency_item.get("CURRENCY")
                or currency_item.get("currency")
                or currency_item.get("CURRENCY_ID")
                or currency_item.get("id")
                or ""
            ).upper()
            if not currency_code or currency_code not in normalized_currency_ids:
                continue

            rate_to_base = self._extract_rate_to_base(currency_item)
            if rate_to_base is not None:
                rates[currency_code] = rate_to_base

        missing_currencies = sorted(normalized_currency_ids - set(rates))
        if missing_currencies:
            raise CurrencyConversionError(
                f"Bitrix24 did not return exchange rates for currencies: {', '.join(missing_currencies)}"
            )

        return rates

    @staticmethod
    def _extract_currency_list(response: Any) -> list[dict[str, Any]]:
        if hasattr(response, "result"):
            result = response.result
        elif isinstance(response, dict):
            result = response.get("result", response)
        else:
            result = response

        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]

        if isinstance(result, dict):
            items = result.get("items") or result.get("currencies") or result.get("result") or []
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]

        return []

    @staticmethod
    def _extract_rate_to_base(currency_item: dict[str, Any]) -> Decimal | None:
        is_base = str(currency_item.get("BASE", "") or currency_item.get("base", "")).upper() in {"Y", "1", "TRUE"}
        is_primary = currency_item.get("is_primary") in {True, "Y", "1", 1}
        if is_base or is_primary:
            return Decimal("1")

        amount = _to_decimal_or_none(currency_item.get("AMOUNT"))
        amount_cnt = _to_decimal_or_none(currency_item.get("AMOUNT_CNT"))
        if amount is not None and amount_cnt not in (None, Decimal("0")):
            return amount / amount_cnt

        current_base_rate = _to_decimal_or_none(currency_item.get("CURRENT_BASE_RATE"))
        if current_base_rate is not None:
            return current_base_rate

        rate = _to_decimal_or_none(currency_item.get("RATE") or currency_item.get("rate"))
        if rate is not None:
            return rate

        return None

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


def _to_decimal_or_none(raw_value: Any) -> Decimal | None:
    if raw_value in (None, ""):
        return None

    try:
        return Decimal(str(raw_value))
    except (InvalidOperation, ValueError):
        return None
