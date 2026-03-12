from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from .bitrix_client import BitrixClientService
from .crm_phone_sync_service import CRMPhoneSyncService
from .full_name_normalizer import normalize_name_words

if TYPE_CHECKING:
    from ..models import Bitrix24Account


@dataclass(frozen=True)
class NameSyncItem:
    entity_type: str
    entity_id: int
    fields_before: dict[str, str]
    fields_after: dict[str, str]
    updated_field_count: int
    updated: bool


class CRMNameSyncService:
    # Robot 2 service: normalize linked contact/company name fields for a deal.
    def __init__(self, bitrix24_account: "Bitrix24Account"):
        self.bitrix_client = BitrixClientService(bitrix24_account)

    def sync_from_document(self, payload: dict[str, Any]) -> list[NameSyncItem]:
        document_token = CRMPhoneSyncService._extract_document_token(payload)
        if not document_token:
            return []

        if document_token.startswith("DEAL_"):
            deal_id = int(document_token.split("_", 1)[1])
            return self._sync_from_deal(deal_id)

        if document_token.startswith("CONTACT_"):
            contact_id = int(document_token.split("_", 1)[1])
            sync_item = self._sync_contact_name(contact_id)
            return [sync_item] if sync_item else []

        if document_token.startswith("COMPANY_"):
            company_id = int(document_token.split("_", 1)[1])
            sync_item = self._sync_company_contact_person(company_id)
            return [sync_item] if sync_item else []

        return []

    def _sync_from_deal(self, deal_id: int) -> list[NameSyncItem]:
        deal_response = self.bitrix_client.call_method("crm.deal.get", {"id": deal_id})
        deal = self._extract_result(deal_response)
        if not isinstance(deal, dict):
            return []

        sync_items: list[NameSyncItem] = []

        contact_id = CRMPhoneSyncService._normalize_entity_id(deal.get("CONTACT_ID"))
        if contact_id is not None:
            sync_item = self._sync_contact_name(contact_id)
            if sync_item is not None:
                sync_items.append(sync_item)

        company_id = CRMPhoneSyncService._normalize_entity_id(deal.get("COMPANY_ID"))
        if company_id is not None:
            sync_item = self._sync_company_contact_person(company_id)
            if sync_item is not None:
                sync_items.append(sync_item)

        return sync_items

    def _sync_contact_name(self, contact_id: int) -> NameSyncItem | None:
        entity_response = self.bitrix_client.call_method("crm.contact.get", {"id": contact_id})
        entity = self._extract_result(entity_response)
        if not isinstance(entity, dict):
            return None

        tracked_fields = ("LAST_NAME", "NAME", "SECOND_NAME")
        return self._sync_entity_fields(
            entity_type="contact",
            entity_id=contact_id,
            update_method="crm.contact.update",
            entity=entity,
            tracked_fields=tracked_fields,
        )

    def _sync_company_contact_person(self, company_id: int) -> NameSyncItem | None:
        entity_response = self.bitrix_client.call_method("crm.company.get", {"id": company_id})
        entity = self._extract_result(entity_response)
        if not isinstance(entity, dict):
            return None

        tracked_fields = ("CONTACT_PERSON",)
        return self._sync_entity_fields(
            entity_type="company",
            entity_id=company_id,
            update_method="crm.company.update",
            entity=entity,
            tracked_fields=tracked_fields,
        )

    def _sync_entity_fields(
        self,
        entity_type: str,
        entity_id: int,
        update_method: str,
        entity: dict[str, Any],
        tracked_fields: tuple[str, ...],
    ) -> NameSyncItem:
        fields_before: dict[str, str] = {}
        fields_after: dict[str, str] = {}
        updated_field_count = 0

        for field_name in tracked_fields:
            raw_value = str(entity.get(field_name, "") or "").strip()
            normalized_value = normalize_name_words(raw_value) if raw_value else ""

            fields_before[field_name] = raw_value
            fields_after[field_name] = normalized_value

            if raw_value and normalized_value != raw_value:
                updated_field_count += 1

        if updated_field_count > 0:
            self.bitrix_client.call_method(
                update_method,
                {
                    "id": entity_id,
                    "fields": fields_after,
                },
            )

        return NameSyncItem(
            entity_type=entity_type,
            entity_id=entity_id,
            fields_before=fields_before,
            fields_after=fields_after,
            updated_field_count=updated_field_count,
            updated=updated_field_count > 0,
        )

    @staticmethod
    def _extract_result(response: Any) -> Any:
        if hasattr(response, "result"):
            return response.result

        if isinstance(response, dict):
            return response.get("result", response)

        return response
