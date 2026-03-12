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
    # Robot 1: normalize linked CRM phone numbers for a deal/contact/company.
    RobotDefinition(
        code="format_phone",
        handler_path="/api/robots/execute/format_phone",
        name=_localized("Форматировать телефон", "Format Phone"),
        description=_localized(
            "Автоматически нормализует все телефоны связанного контакта и компании",
            "Automatically normalizes all phones of the linked contact and company",
        ),
        properties={
            "default_country_code": {
                "Name": _localized("Код страны по умолчанию", "Default country code"),
                "Type": "string",
                "Required": "N",
                "Default": "7",
            },
        },
        return_properties={
            "processed_entities": {
                "Name": _localized("Обработано сущностей", "Processed entities"),
                "Type": "int",
            },
            "updated_entities": {
                "Name": _localized("Изменено сущностей", "Updated entities"),
                "Type": "int",
            },
            "updated_phone_count": {
                "Name": _localized("Изменено телефонов", "Updated phone count"),
                "Type": "int",
            },
            "entity_summary": {
                "Name": _localized("Сводка по сущностям", "Entity summary"),
                "Type": "string",
            },
        },
    ),
    # Robot 2: normalize participant names in linked CRM cards for a deal.
    RobotDefinition(
        code="normalize_full_name",
        handler_path="/api/robots/execute/normalize_full_name",
        name=_localized("Нормализовать ФИО", "Normalize Full Name"),
        description=_localized(
            "Автоматически нормализует имена участников сделки в связанных карточках CRM",
            "Automatically normalizes participant names in linked CRM cards",
        ),
        return_properties={
            "processed_entities": {
                "Name": _localized("Обработано сущностей", "Processed entities"),
                "Type": "int",
            },
            "updated_entities": {
                "Name": _localized("Изменено сущностей", "Updated entities"),
                "Type": "int",
            },
            "updated_field_count": {
                "Name": _localized("Изменено полей имени", "Updated name fields"),
                "Type": "int",
            },
            "entity_summary": {
                "Name": _localized("Сводка по сущностям", "Entity summary"),
                "Type": "string",
            },
        },
    ),
    # Robot 3: sum all deals for the current deal client and write the result to the deal timeline.
    RobotDefinition(
        code="sum_client_deals",
        handler_path="/api/robots/execute/sum_client_deals",
        name=_localized("Сумма сделок клиента", "Sum Client Deals"),
        description=_localized(
            "Считает сумму сделок клиента по текущей сделке и пишет результат в таймлайн сделки",
            "Calculates the client deal total for the current deal and writes the result to the deal timeline",
        ),
        return_properties={
            "deal_count": {
                "Name": _localized("Количество сделок клиента", "Client deal count"),
                "Type": "int",
            },
            "total_amount": {
                "Name": _localized("Сумма сделок клиента", "Client deal total"),
                "Type": "string",
            },
            "currency_id": {
                "Name": _localized("Валюта", "Currency"),
                "Type": "string",
            },
            "client_entity_type": {
                "Name": _localized("Тип клиента", "Client entity type"),
                "Type": "string",
            },
            "client_entity_id": {
                "Name": _localized("ID клиента", "Client entity ID"),
                "Type": "string",
            },
        },
    ),
    # Robot 4: count overdue tasks of the deal responsible and write the result to the deal timeline.
    RobotDefinition(
        code="count_overdue_tasks",
        handler_path="/api/robots/execute/count_overdue_tasks",
        name=_localized("Просроченные задачи ответственного", "Count Overdue Tasks"),
        description=_localized(
            "Считает просроченные задачи ответственного по текущей сделке и пишет результат в таймлайн сделки",
            "Counts overdue tasks of the current deal responsible user and writes the result to the deal timeline",
        ),
        return_properties={
            "responsible_user_id": {
                "Name": _localized("ID ответственного", "Responsible user ID"),
                "Type": "string",
            },
            "total_tasks_checked": {
                "Name": _localized("Проверено задач", "Tasks checked"),
                "Type": "int",
            },
            "overdue_task_count": {
                "Name": _localized("Просрочено задач", "Overdue task count"),
                "Type": "int",
            },
        },
    ),
]


def get_robot_definitions() -> list[RobotDefinition]:
    return ROBOT_DEFINITIONS


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
