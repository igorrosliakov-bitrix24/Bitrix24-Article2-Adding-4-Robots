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


def _normalize_country_code(raw_country_code: str) -> str:
    digits = "".join(char for char in raw_country_code if char.isdigit())
    return digits or "7"


def _extract_digits(raw_phone: str) -> str:
    return "".join(char for char in raw_phone if char.isdigit())


def _format_phone(raw_phone: str, default_country_code: str) -> tuple[str, str, bool]:
    digits_only = _extract_digits(raw_phone)
    country_code = _normalize_country_code(default_country_code)

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


def handle_format_phone(context: RobotExecutionContext) -> RobotHandlerResult:
    raw_phone = _read_property(
        context.payload,
        ("phone",),
        ("PHONE",),
        ("properties", "phone"),
        ("properties", "PHONE"),
    )
    default_country_code = _read_property(
        context.payload,
        ("default_country_code",),
        ("DEFAULT_COUNTRY_CODE",),
        ("properties", "default_country_code"),
        ("properties", "DEFAULT_COUNTRY_CODE"),
    )

    formatted_phone, digits_only, is_valid = _format_phone(raw_phone, default_country_code)

    return RobotHandlerResult(
        return_values={
            "formatted_phone": formatted_phone,
            "digits_only": digits_only,
            "is_valid": "Y" if is_valid else "N",
        },
        log_message=(
            f"format_phone processed input='{raw_phone}', "
            f"formatted='{formatted_phone}', "
            f"valid={'Y' if is_valid else 'N'}, "
            f"country_code='{_normalize_country_code(default_country_code)}'"
        ),
    )
