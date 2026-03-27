from decimal import Decimal, InvalidOperation

from ..services.crm_timeline_service import CRMTimelineService
from ..services.deal_sum_service import CurrencyConversionError, DealSumResult, DealSumService
from ..services.robot_types import RobotExecutionContext, RobotHandlerResult


def _debug_result(payload: dict) -> DealSumResult | None:
    debug_current_deal = payload.get("debug_current_deal")
    debug_deals = payload.get("debug_deals")

    if not isinstance(debug_current_deal, dict) or not isinstance(debug_deals, list):
        return None

    company_id = debug_current_deal.get("COMPANY_ID")
    contact_id = debug_current_deal.get("CONTACT_ID")
    currency_id = str(debug_current_deal.get("CURRENCY_ID", "") or "")
    deal_id = str(debug_current_deal.get("ID", "") or "")

    if company_id not in (None, "", 0, "0"):
        client_entity_type = "company"
        client_entity_id = str(company_id)
        filtered_deals = [
            deal_item for deal_item in debug_deals
            if isinstance(deal_item, dict) and str(deal_item.get("COMPANY_ID", "")) == client_entity_id
        ]
    elif contact_id not in (None, "", 0, "0"):
        client_entity_type = "contact"
        client_entity_id = str(contact_id)
        filtered_deals = [
            deal_item for deal_item in debug_deals
            if isinstance(deal_item, dict) and str(deal_item.get("CONTACT_ID", "")) == client_entity_id
        ]
    else:
        filtered_deals = []
        client_entity_type = ""
        client_entity_id = ""

    total_amount = Decimal("0.00")
    for deal_item in filtered_deals:
        total_amount += _to_decimal(deal_item.get("OPPORTUNITY"))

    return DealSumResult(
        deal_count=len(filtered_deals),
        total_amount=f"{total_amount.quantize(Decimal('0.01'))}",
        currency_id=currency_id,
        client_entity_type=client_entity_type,
        client_entity_id=client_entity_id,
        current_deal_id=deal_id,
    )


def handle_sum_client_deals(context: RobotExecutionContext) -> RobotHandlerResult:
    # Robot 3 orchestration: calculate the client deal total and expose it to BP plus deal timeline.
    try:
        if context.bitrix24_account is not None:
            result = DealSumService(context.bitrix24_account).summarize_from_document(context.payload)
        else:
            result = _debug_result(context.payload)
    except CurrencyConversionError as error:
        if context.bitrix24_account is not None:
            CRMTimelineService(context.bitrix24_account).add_comment_from_document(
                context.payload,
                f"Не удалось посчитать сумму сделок клиента в USD: {error}",
            )

        return RobotHandlerResult(
            return_values={
                "deal_count": "0",
                "total_amount": "0.00",
                "currency_id": DealSumService.TARGET_CURRENCY_ID,
                "client_entity_type": "",
                "client_entity_id": "",
            },
            log_message=f"sum_client_deals currency conversion error: {error}",
        )

    if result is None:
        return RobotHandlerResult(
            return_values={
                "deal_count": "0",
                "total_amount": "0.00",
                "currency_id": DealSumService.TARGET_CURRENCY_ID,
                "client_entity_type": "",
                "client_entity_id": "",
            },
            log_message="sum_client_deals could not resolve current deal context",
        )

    timeline_message = (
        f"Сумма сделок клиента: {result.total_amount} {result.currency_id}".strip()
        + f" | сделок: {result.deal_count}"
    )
    if result.client_entity_type and result.client_entity_id:
        timeline_message += f" | клиент: {result.client_entity_type}:{result.client_entity_id}"

    if context.bitrix24_account is not None:
        CRMTimelineService(context.bitrix24_account).add_comment_from_document(
            context.payload,
            timeline_message,
        )

    return RobotHandlerResult(
        return_values={
            "deal_count": str(result.deal_count),
            "total_amount": result.total_amount,
            "currency_id": result.currency_id,
            "client_entity_type": result.client_entity_type,
            "client_entity_id": result.client_entity_id,
        },
        log_message=(
            f"sum_client_deals total_amount={result.total_amount}, "
            f"currency='{result.currency_id}', "
            f"deal_count={result.deal_count}, "
            f"client='{result.client_entity_type}:{result.client_entity_id}'"
        ),
    )


def _to_decimal(raw_value) -> Decimal:
    try:
        return Decimal(str(raw_value or 0))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")
