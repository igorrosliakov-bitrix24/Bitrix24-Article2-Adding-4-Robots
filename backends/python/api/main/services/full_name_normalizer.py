from dataclasses import dataclass
import re


DEFAULT_INPUT_FORMAT = "last_first_middle"
DEFAULT_OUTPUT_FORMAT = "last_first_middle"

SUPPORTED_INPUT_FORMATS = {
    "last_first_middle",
    "first_middle_last",
    "first_last",
}

SUPPORTED_OUTPUT_FORMATS = {
    "last_first_middle",
    "first_middle_last",
    "first_last",
    "last_with_initials",
    "initials_last",
}


@dataclass(frozen=True)
class FullNameNormalizationResult:
    raw_full_name: str
    normalized_full_name: str
    last_name: str
    first_name: str
    middle_name: str
    input_format: str
    output_format: str
    parts_count: int
    is_valid: bool


def normalize_full_name(
    raw_full_name: str,
    input_format: str = DEFAULT_INPUT_FORMAT,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
) -> FullNameNormalizationResult:
    normalized_input_format = normalize_input_format(input_format)
    normalized_output_format = normalize_output_format(output_format)
    tokens = _tokenize_full_name(raw_full_name)

    if not tokens:
        return FullNameNormalizationResult(
            raw_full_name=raw_full_name,
            normalized_full_name="",
            last_name="",
            first_name="",
            middle_name="",
            input_format=normalized_input_format,
            output_format=normalized_output_format,
            parts_count=0,
            is_valid=False,
        )

    last_name, first_name, middle_name = _parse_tokens(tokens, normalized_input_format)
    normalized_full_name = _compose_full_name(
        last_name,
        first_name,
        middle_name,
        normalized_output_format,
    )

    return FullNameNormalizationResult(
        raw_full_name=raw_full_name,
        normalized_full_name=normalized_full_name,
        last_name=last_name,
        first_name=first_name,
        middle_name=middle_name,
        input_format=normalized_input_format,
        output_format=normalized_output_format,
        parts_count=len(tokens),
        is_valid=bool(normalized_full_name),
    )


def normalize_input_format(raw_format: str) -> str:
    normalized = (raw_format or "").strip().lower()
    return normalized if normalized in SUPPORTED_INPUT_FORMATS else DEFAULT_INPUT_FORMAT


def normalize_output_format(raw_format: str) -> str:
    normalized = (raw_format or "").strip().lower()
    return normalized if normalized in SUPPORTED_OUTPUT_FORMATS else DEFAULT_OUTPUT_FORMAT


def _tokenize_full_name(raw_full_name: str) -> list[str]:
    cleaned_value = re.sub(r"[^\w\s\-']", " ", raw_full_name, flags=re.UNICODE)
    collapsed = re.sub(r"\s+", " ", cleaned_value, flags=re.UNICODE).strip()

    if not collapsed:
        return []

    return [_normalize_token(token) for token in collapsed.split(" ") if token]


def _normalize_token(token: str) -> str:
    hyphenated_parts = []
    for hyphen_part in token.split("-"):
        apostrophe_parts = []
        for apostrophe_part in hyphen_part.split("'"):
            if apostrophe_part:
                apostrophe_parts.append(apostrophe_part[:1].upper() + apostrophe_part[1:].lower())
            else:
                apostrophe_parts.append("")
        hyphenated_parts.append("'".join(apostrophe_parts))

    return "-".join(hyphenated_parts)


def _parse_tokens(tokens: list[str], input_format: str) -> tuple[str, str, str]:
    if input_format == "first_middle_last":
        first_name = tokens[0] if len(tokens) >= 1 else ""
        last_name = tokens[-1] if len(tokens) >= 2 else ""
        middle_name = " ".join(tokens[1:-1]) if len(tokens) >= 3 else ""
        return last_name, first_name, middle_name

    if input_format == "first_last":
        first_name = tokens[0] if len(tokens) >= 1 else ""
        last_name = tokens[1] if len(tokens) >= 2 else ""
        middle_name = " ".join(tokens[2:]) if len(tokens) >= 3 else ""
        return last_name, first_name, middle_name

    last_name = tokens[0] if len(tokens) >= 1 else ""
    first_name = tokens[1] if len(tokens) >= 2 else ""
    middle_name = " ".join(tokens[2:]) if len(tokens) >= 3 else ""
    return last_name, first_name, middle_name


def _compose_full_name(
    last_name: str,
    first_name: str,
    middle_name: str,
    output_format: str,
) -> str:
    if output_format == "first_middle_last":
        return _join_parts(first_name, middle_name, last_name)

    if output_format == "first_last":
        return _join_parts(first_name, last_name)

    if output_format == "last_with_initials":
        return _join_parts(last_name, _build_initials(first_name, middle_name))

    if output_format == "initials_last":
        return _join_parts(_build_initials(first_name, middle_name), last_name)

    return _join_parts(last_name, first_name, middle_name)


def _build_initials(first_name: str, middle_name: str) -> str:
    initials = []

    for part in _split_name_parts(first_name):
        if part:
            initials.append(f"{part[0]}.")

    for part in _split_name_parts(middle_name):
        if part:
            initials.append(f"{part[0]}.")

    return "".join(initials)


def _split_name_parts(raw_value: str) -> list[str]:
    if not raw_value:
        return []

    return [part for part in raw_value.split(" ") if part]


def _join_parts(*parts: str) -> str:
    return " ".join(part for part in parts if part).strip()


def normalize_name_words(raw_value: str) -> str:
    tokens = _tokenize_full_name(raw_value)
    return _join_parts(*tokens)
