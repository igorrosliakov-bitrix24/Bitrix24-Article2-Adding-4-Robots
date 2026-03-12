from datetime import datetime, timedelta, timezone
import uuid
from typing import cast

from b24pysdk.bitrix_api.credentials import OAuthPlacementData
from b24pysdk.error import BitrixValidationError
from b24pysdk.utils.types import JSONDict

from ..models import Bitrix24Account


def extract_robot_auth_dict(payload: JSONDict) -> dict | None:
    auth_payload = payload.get("auth")
    if isinstance(auth_payload, dict):
        return auth_payload

    extracted_auth = {}
    for source_key, target_key in (
        ("auth[access_token]", "access_token"),
        ("auth[refresh_token]", "refresh_token"),
        ("auth[domain]", "domain"),
        ("auth[member_id]", "member_id"),
        ("auth[expires_in]", "expires_in"),
        ("auth[status]", "status"),
        ("auth[user_id]", "user_id"),
        ("auth[application_token]", "application_token"),
    ):
        if source_key in payload:
            extracted_auth[target_key] = payload[source_key]

    return extracted_auth or None


def normalize_robot_auth_payload(payload: JSONDict) -> JSONDict:
    auth_payload = extract_robot_auth_dict(payload)
    if not isinstance(auth_payload, dict):
        return payload

    domain = auth_payload.get("domain") or payload.get("DOMAIN") or payload.get("domain") or ""
    protocol = 1
    if isinstance(domain, str) and domain.startswith("http://"):
        protocol = 0

    normalized_payload = dict(payload)
    normalized_payload.update({
        "DOMAIN": str(domain).replace("https://", "").replace("http://", ""),
        "PROTOCOL": protocol,
        "AUTH_ID": auth_payload.get("access_token", payload.get("AUTH_ID", "")),
        "AUTH_EXPIRES": auth_payload.get("expires_in", payload.get("AUTH_EXPIRES", 3600)),
        "REFRESH_ID": auth_payload.get("refresh_token", payload.get("REFRESH_ID", "")),
        "REFRESH_TOKEN": auth_payload.get("refresh_token", payload.get("REFRESH_TOKEN", "")),
        "member_id": auth_payload.get("member_id", payload.get("member_id", "")),
        "status": auth_payload.get("status", payload.get("status", "F")),
    })

    return cast(JSONDict, normalized_payload)


def build_account_from_robot_auth(payload: JSONDict) -> Bitrix24Account | None:
    auth_payload = extract_robot_auth_dict(payload)
    if not isinstance(auth_payload, dict):
        return None

    domain = auth_payload.get("domain") or payload.get("DOMAIN") or payload.get("domain") or ""
    access_token = auth_payload.get("access_token") or payload.get("AUTH_ID")
    refresh_token = auth_payload.get("refresh_token") or payload.get("REFRESH_ID") or payload.get("REFRESH_TOKEN")
    member_id = auth_payload.get("member_id") or payload.get("member_id") or ""

    if not isinstance(domain, str) or not domain.strip():
        raise BitrixValidationError("Robot auth payload is missing domain")
    if not isinstance(access_token, str) or not access_token.strip():
        raise BitrixValidationError("Robot auth payload is missing access token")
    if not isinstance(refresh_token, str) or not refresh_token.strip():
        raise BitrixValidationError("Robot auth payload is missing refresh token")
    if not isinstance(member_id, str) or not member_id.strip():
        raise BitrixValidationError("Robot auth payload is missing member_id")

    expires_in_raw = auth_payload.get("expires_in", payload.get("AUTH_EXPIRES", 3600))
    try:
        expires_in = int(expires_in_raw)
    except (TypeError, ValueError):
        expires_in = 3600

    domain_value = domain.replace("https://", "").replace("http://", "")
    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(seconds=max(expires_in, 0))

    return Bitrix24Account(
        id=uuid.uuid4(),
        b24_user_id=int(payload.get("user_id", auth_payload.get("user_id", 0)) or 0),
        is_b24_user_admin=False,
        member_id=member_id,
        is_master_account=None,
        domain_url=domain_value,
        status=str(auth_payload.get("status", payload.get("status", "F"))),
        application_token=str(payload.get("APP_SID", auth_payload.get("application_token", "")) or ""),
        application_version=int(payload.get("appVersion", 1) or 1),
        comment=None,
        access_token=access_token,
        refresh_token=refresh_token,
        expires=int(expires_at.timestamp()),
        expires_in=expires_in,
        current_scope=None,
    )


def resolve_bitrix24_account(payload: JSONDict) -> Bitrix24Account:
    robot_account = build_account_from_robot_auth(payload)
    if robot_account is not None:
        return robot_account

    normalized_payload = normalize_robot_auth_payload(payload)
    oauth_placement_data = OAuthPlacementData.from_dict(normalized_payload)
    bitrix24_account, _ = Bitrix24Account.update_or_create_from_oauth_placement_data(oauth_placement_data)
    return bitrix24_account
