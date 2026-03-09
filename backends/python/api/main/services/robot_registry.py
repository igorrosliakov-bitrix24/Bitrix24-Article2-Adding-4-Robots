from dataclasses import dataclass, field
from typing import Any


def _localized(ru_value: str, en_value: str) -> dict[str, str]:
    return {
        "ru": ru_value,
        "en": en_value,
    }


@dataclass(frozen=True)
class RobotDefinition:
    code: str
    handler_path: str
    name: dict[str, str]
    description: dict[str, str]
    properties: dict[str, Any] = field(default_factory=dict)
    return_properties: dict[str, Any] = field(default_factory=dict)
    use_subscription: str = "Y"

    def handler_url(self, app_base_url: str) -> str:
        return f"{app_base_url.rstrip('/')}{self.handler_path}"

    def to_registration_payload(self, app_base_url: str, auth_user_id: int) -> dict[str, Any]:
        payload = {
            "CODE": self.code,
            "HANDLER": self.handler_url(app_base_url),
            "AUTH_USER_ID": auth_user_id,
            "USE_SUBSCRIPTION": self.use_subscription,
            "NAME": self.name,
            "DESCRIPTION": self.description,
        }

        if self.properties:
            payload["PROPERTIES"] = self.properties

        if self.return_properties:
            payload["RETURN_PROPERTIES"] = self.return_properties

        return payload


ROBOT_DEFINITIONS = [
    RobotDefinition(
        code="format_phone",
        handler_path="/api/robots/execute/format_phone",
        name=_localized("Форматировать телефон", "Format Phone"),
        description=_localized(
            "Приводит номер телефона к единому формату и возвращает результат",
            "Converts a phone number to a unified format and returns the result",
        ),
        properties={
            "phone": {
                "Name": _localized("Телефон", "Phone"),
                "Type": "string",
                "Required": "Y",
            },
            "default_country_code": {
                "Name": _localized("Код страны по умолчанию", "Default country code"),
                "Type": "string",
                "Required": "N",
                "Default": "7",
            },
        },
        return_properties={
            "formatted_phone": {
                "Name": _localized("Форматированный телефон", "Formatted phone"),
                "Type": "string",
            },
            "digits_only": {
                "Name": _localized("Только цифры", "Digits only"),
                "Type": "string",
            },
            "is_valid": {
                "Name": _localized("Валиден", "Is valid"),
                "Type": "bool",
            },
        },
    ),
    RobotDefinition(
        code="system_ping",
        handler_path="/api/robots/execute/system_ping",
        name=_localized("Проверка каркаса роботов", "Robot Skeleton Check"),
        description=_localized(
            "Временный диагностический робот для локальной отладки",
            "Temporary diagnostic robot for local debugging",
        ),
        return_properties={
            "message": {
                "Name": _localized("Сообщение", "Message"),
                "Type": "string",
            },
            "mode": {
                "Name": _localized("Режим", "Mode"),
                "Type": "string",
            },
        },
    ),
]


def get_robot_definitions() -> list[RobotDefinition]:
    return [robot_definition for robot_definition in ROBOT_DEFINITIONS if robot_definition.code != "system_ping"]


def get_robot_definition(robot_code: str) -> RobotDefinition | None:
    for robot_definition in get_robot_definitions():
        if robot_definition.code == robot_code:
            return robot_definition

    return None


def get_robot_catalog(app_base_url: str) -> list[dict[str, Any]]:
    catalog = []

    for robot_definition in get_robot_definitions():
        catalog.append({
            "code": robot_definition.code,
            "name": robot_definition.name,
            "description": robot_definition.description,
            "handler_url": robot_definition.handler_url(app_base_url),
            "use_subscription": robot_definition.use_subscription,
            "properties": robot_definition.properties,
            "return_properties": robot_definition.return_properties,
        })

    return catalog
