from ..services.crm_name_sync_service import CRMNameSyncService, NameSyncItem
from ..services.full_name_normalizer import normalize_name_words
from ..services.robot_types import RobotExecutionContext, RobotHandlerResult


def _debug_sync_items(payload: dict) -> list[NameSyncItem]:
    debug_entities = payload.get("debug_entities")
    if not isinstance(debug_entities, dict):
        return []

    sync_items: list[NameSyncItem] = []

    contact_data = debug_entities.get("contact")
    if isinstance(contact_data, dict):
        fields_before = {
            "LAST_NAME": str(contact_data.get("LAST_NAME", "") or "").strip(),
            "NAME": str(contact_data.get("NAME", "") or "").strip(),
            "SECOND_NAME": str(contact_data.get("SECOND_NAME", "") or "").strip(),
        }
        fields_after = {
            "LAST_NAME": _normalize_local_value(fields_before["LAST_NAME"]),
            "NAME": _normalize_local_value(fields_before["NAME"]),
            "SECOND_NAME": _normalize_local_value(fields_before["SECOND_NAME"]),
        }
        updated_field_count = sum(
            1
            for field_name, raw_value in fields_before.items()
            if raw_value and fields_after[field_name] != raw_value
        )
        sync_items.append(
            NameSyncItem(
                entity_type="contact",
                entity_id=int(contact_data.get("ID", 0)),
                fields_before=fields_before,
                fields_after=fields_after,
                updated_field_count=updated_field_count,
                updated=updated_field_count > 0,
            )
        )

    company_data = debug_entities.get("company")
    if isinstance(company_data, dict):
        fields_before = {
            "TITLE": str(company_data.get("TITLE", "") or "").strip(),
            "CONTACT_PERSON": str(company_data.get("CONTACT_PERSON", "") or "").strip(),
        }
        fields_after = {
            "TITLE": _normalize_local_value(fields_before["TITLE"]),
            "CONTACT_PERSON": _normalize_local_value(fields_before["CONTACT_PERSON"]),
        }
        updated_field_count = sum(
            1
            for field_name, raw_value in fields_before.items()
            if raw_value and fields_after[field_name] != raw_value
        )
        sync_items.append(
            NameSyncItem(
                entity_type="company",
                entity_id=int(company_data.get("ID", 0)),
                fields_before=fields_before,
                fields_after=fields_after,
                updated_field_count=updated_field_count,
                updated=updated_field_count > 0,
            )
        )

    return sync_items


def _normalize_local_value(raw_value: str) -> str:
    return normalize_name_words(raw_value) if raw_value else ""


def handle_normalize_full_name(context: RobotExecutionContext) -> RobotHandlerResult:
    # Robot 2 orchestration: sync participant names in linked CRM cards and return a summary.
    if context.bitrix24_account is not None:
        sync_items = CRMNameSyncService(context.bitrix24_account).sync_from_document(context.payload)
    else:
        sync_items = _debug_sync_items(context.payload)

    processed_entities = len(sync_items)
    updated_entities = sum(1 for item in sync_items if item.updated)
    updated_field_count = sum(item.updated_field_count for item in sync_items)
    entity_summary = ", ".join(
        f"{item.entity_type}:{item.entity_id}:{item.updated_field_count}" for item in sync_items
    )

    return RobotHandlerResult(
        return_values={
            "processed_entities": str(processed_entities),
            "updated_entities": str(updated_entities),
            "updated_field_count": str(updated_field_count),
            "entity_summary": entity_summary,
        },
        log_message=(
            f"normalize_full_name processed_entities={processed_entities}, "
            f"updated_entities={updated_entities}, "
            f"updated_field_count={updated_field_count}, "
            f"summary='{entity_summary}'"
        ),
    )
