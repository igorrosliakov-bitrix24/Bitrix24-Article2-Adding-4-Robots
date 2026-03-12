from ..services.crm_phone_sync_service import CRMPhoneSyncService, PhoneSyncItem, format_phone_value, normalize_country_code
from ..services.robot_types import RobotExecutionContext, RobotHandlerResult


def _read_property(payload: dict, *paths: tuple[str, ...]) -> str:
    for path in paths:
        current_value = payload

        for key in path:
            if not isinstance(current_value, dict) or key not in current_value:
                current_value = None
                break
            current_value = current_value[key]

        if isinstance(current_value, str) and current_value.strip():
            return current_value.strip()

    return ""


def _debug_sync_items(payload: dict, default_country_code: str) -> list[PhoneSyncItem]:
    debug_entities = payload.get("debug_entities")
    if not isinstance(debug_entities, dict):
        return []

    sync_items: list[PhoneSyncItem] = []

    for entity_type in ("contact", "company"):
        entity_data = debug_entities.get(entity_type)
        if not isinstance(entity_data, dict):
            continue

        phones_before = entity_data.get("PHONE")
        if not isinstance(phones_before, list):
            continue

        phones_after = []
        updated_phone_count = 0

        for phone_item in phones_before:
            if not isinstance(phone_item, dict):
                continue

            phone_value = str(phone_item.get("VALUE", ""))
            formatted_phone, _, is_valid = format_phone_value(phone_value, default_country_code)
            updated_value = formatted_phone if is_valid else phone_value
            if updated_value != phone_value:
                updated_phone_count += 1

            phones_after.append({
                "VALUE": updated_value,
                "VALUE_TYPE": phone_item.get("VALUE_TYPE", "WORK"),
            })

        sync_items.append(
            PhoneSyncItem(
                entity_type=entity_type,
                entity_id=int(entity_data.get("ID", 0)),
                phones_before=phones_before,
                phones_after=phones_after,
                updated_phone_count=updated_phone_count,
                updated=updated_phone_count > 0,
            )
        )

    return sync_items


def handle_format_phone(context: RobotExecutionContext) -> RobotHandlerResult:
    # Robot 1 orchestration: resolve input, sync CRM phones, return a short summary.
    default_country_code = _read_property(
        context.payload,
        ("default_country_code",),
        ("DEFAULT_COUNTRY_CODE",),
        ("properties", "default_country_code"),
        ("properties", "DEFAULT_COUNTRY_CODE"),
    )

    if context.bitrix24_account is not None:
        sync_items = CRMPhoneSyncService(context.bitrix24_account).sync_from_document(
            context.payload,
            default_country_code,
        )
    else:
        sync_items = _debug_sync_items(context.payload, default_country_code)

    total_entities = len(sync_items)
    updated_entities = sum(1 for item in sync_items if item.updated)
    updated_phone_count = sum(item.updated_phone_count for item in sync_items)

    entity_summary_parts = []
    for item in sync_items:
        entity_summary_parts.append(f"{item.entity_type}:{item.entity_id}:{item.updated_phone_count}")

    entity_summary = ", ".join(entity_summary_parts)

    return RobotHandlerResult(
        return_values={
            "processed_entities": str(total_entities),
            "updated_entities": str(updated_entities),
            "updated_phone_count": str(updated_phone_count),
            "entity_summary": entity_summary,
        },
        log_message=(
            f"format_phone processed entities={total_entities}, "
            f"updated_entities={updated_entities}, "
            f"updated_phone_count={updated_phone_count}, "
            f"country_code='{normalize_country_code(default_country_code)}', "
            f"summary='{entity_summary}'"
        ),
    )
