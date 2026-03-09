import logging
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from .bitrix_client import BitrixClientService

if TYPE_CHECKING:
    from ..models import Bitrix24Account


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PhoneSyncItem:
    entity_type: str
    entity_id: int
    phones_before: list[dict[str, Any]]
    phones_after: list[dict[str, Any]]
    updated_phone_count: int
    updated: bool


class CRMPhoneSyncService:
    def __init__(self, bitrix24_account: "Bitrix24Account"):
        self.bitrix_client = BitrixClientService(bitrix24_account)

    def sync_from_document(self, payload: dict[str, Any], default_country_code: str) -> list[PhoneSyncItem]:
        document_token = self._extract_document_token(payload)
        logger.info(
            "format_phone sync_from_document token=%r payload_document_keys=%s",
            document_token,
            self._collect_document_debug_keys(payload),
        )
        if not document_token:
            logger.warning("format_phone document token is missing")
            return []

        if document_token.startswith("DEAL_"):
            deal_id = int(document_token.split("_", 1)[1])
            logger.info("format_phone detected deal document deal_id=%s", deal_id)
            return self._sync_from_deal(deal_id, default_country_code)

        if document_token.startswith("CONTACT_"):
            contact_id = int(document_token.split("_", 1)[1])
            logger.info("format_phone detected contact document contact_id=%s", contact_id)
            sync_item = self._sync_entity_phones("contact", contact_id, default_country_code)
            return [sync_item] if sync_item else []

        if document_token.startswith("COMPANY_"):
            company_id = int(document_token.split("_", 1)[1])
            logger.info("format_phone detected company document company_id=%s", company_id)
            sync_item = self._sync_entity_phones("company", company_id, default_country_code)
            return [sync_item] if sync_item else []

        logger.warning("format_phone unsupported document token=%r", document_token)
        return []

    def _sync_from_deal(self, deal_id: int, default_country_code: str) -> list[PhoneSyncItem]:
        deal_response = self.bitrix_client.call_method("crm.deal.get", {"id": deal_id})
        deal = self._extract_result(deal_response)
        logger.info("format_phone deal_id=%s raw_deal_result=%r", deal_id, deal)

        sync_items: list[PhoneSyncItem] = []
        for entity_type, entity_key in (("contact", "CONTACT_ID"), ("company", "COMPANY_ID")):
            entity_id = self._normalize_entity_id(deal.get(entity_key)) if isinstance(deal, dict) else None
            if entity_id is None:
                logger.info(
                    "format_phone deal_id=%s has no linked %s via %s value=%r",
                    deal_id,
                    entity_type,
                    entity_key,
                    deal.get(entity_key) if isinstance(deal, dict) else None,
                )
                continue

            logger.info(
                "format_phone deal_id=%s linked %s_id=%s via %s",
                deal_id,
                entity_type,
                entity_id,
                entity_key,
            )
            sync_item = self._sync_entity_phones(entity_type, entity_id, default_country_code)
            if sync_item is not None:
                sync_items.append(sync_item)

        if not sync_items:
            logger.warning("format_phone deal_id=%s produced no sync items", deal_id)

        return sync_items

    def _sync_entity_phones(
        self,
        entity_type: str,
        entity_id: int,
        default_country_code: str,
    ) -> PhoneSyncItem | None:
        get_method = f"crm.{entity_type}.get"
        update_method = f"crm.{entity_type}.update"

        entity_response = self.bitrix_client.call_method(get_method, {"id": entity_id})
        entity = self._extract_result(entity_response)
        if not isinstance(entity, dict):
            logger.warning(
                "format_phone %s_id=%s returned non-dict entity=%r",
                entity_type,
                entity_id,
                entity,
            )
            return None

        phones_before = entity.get("PHONE")
        if not isinstance(phones_before, list):
            phones_before = []
        logger.info(
            "format_phone %s_id=%s phones_before_count=%s phones_before=%r",
            entity_type,
            entity_id,
            len(phones_before),
            phones_before,
        )

        phones_after: list[dict[str, Any]] = []
        updated_phone_count = 0

        for phone_item in phones_before:
            if not isinstance(phone_item, dict):
                continue

            phone_value = str(phone_item.get("VALUE", ""))
            formatted_phone, _, is_valid = format_phone_value(phone_value, default_country_code)

            updated_phone = {
                "VALUE": formatted_phone if is_valid else phone_value,
                "VALUE_TYPE": phone_item.get("VALUE_TYPE", "WORK"),
            }

            if phone_item.get("ID"):
                updated_phone["ID"] = phone_item["ID"]

            if phone_item.get("TYPE_ID"):
                updated_phone["TYPE_ID"] = phone_item["TYPE_ID"]

            if updated_phone["VALUE"] != phone_value:
                updated_phone_count += 1

            phones_after.append(updated_phone)

        if updated_phone_count > 0:
            logger.info(
                "format_phone %s_id=%s updating phones_after=%r",
                entity_type,
                entity_id,
                phones_after,
            )
            self.bitrix_client.call_method(
                update_method,
                {
                    "id": entity_id,
                    "fields": {
                        "PHONE": phones_after,
                    },
                },
            )
        else:
            logger.info(
                "format_phone %s_id=%s no phone changes detected phones_after=%r",
                entity_type,
                entity_id,
                phones_after,
            )

        return PhoneSyncItem(
            entity_type=entity_type,
            entity_id=entity_id,
            phones_before=phones_before,
            phones_after=phones_after,
            updated_phone_count=updated_phone_count,
            updated=updated_phone_count > 0,
        )

    @staticmethod
    def _extract_result(response: Any) -> Any:
        if hasattr(response, "result"):
            return response.result

        if isinstance(response, dict):
            return response.get("result", response)

        return response

    @staticmethod
    def _extract_document_token(payload: dict[str, Any]) -> str | None:
        for key in ("document_id", "DOCUMENT_ID"):
            document_id = payload.get(key)

            if isinstance(document_id, list) and len(document_id) >= 3 and isinstance(document_id[2], str):
                return document_id[2]

            if isinstance(document_id, str) and document_id:
                return document_id

        for key_prefix in ("document_id", "DOCUMENT_ID"):
            document_token = payload.get(f"{key_prefix}[2]")
            if isinstance(document_token, str) and document_token:
                return document_token

            document_token = payload.get(f"{key_prefix}[]")
            if isinstance(document_token, list) and len(document_token) >= 3 and isinstance(document_token[2], str):
                return document_token[2]
            if isinstance(document_token, str) and document_token:
                return document_token

        return None

    @staticmethod
    def _collect_document_debug_keys(payload: dict[str, Any]) -> dict[str, Any]:
        document_keys = {}
        for key in payload:
            if "document" in key.lower():
                document_keys[key] = payload[key]
        return document_keys

    @staticmethod
    def _normalize_entity_id(value: Any) -> int | None:
        if value in (None, "", 0, "0"):
            return None

        if isinstance(value, int):
            return value

        if isinstance(value, str) and value.isdigit():
            return int(value)

        return None


def normalize_country_code(raw_country_code: str) -> str:
    digits = "".join(char for char in raw_country_code if char.isdigit())
    return digits or "7"


def extract_digits(raw_phone: str) -> str:
    return "".join(char for char in raw_phone if char.isdigit())


def format_phone_value(raw_phone: str, default_country_code: str) -> tuple[str, str, bool]:
    digits_only = extract_digits(raw_phone)
    country_code = normalize_country_code(default_country_code)

    if not digits_only:
        return "", "", False

    if len(digits_only) == 11 and digits_only.startswith("8"):
        digits_only = f"7{digits_only[1:]}"
    elif len(digits_only) == 10:
        digits_only = f"{country_code}{digits_only}"
    elif raw_phone.strip().startswith("00") and len(digits_only) > 2:
        digits_only = digits_only[2:]

    is_valid = 11 <= len(digits_only) <= 15
    formatted_phone = f"+{digits_only}" if is_valid else digits_only

    return formatted_phone, digits_only, is_valid
