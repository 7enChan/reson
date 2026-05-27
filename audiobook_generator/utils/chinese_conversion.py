from typing import Dict, List, Tuple


CHINESE_CONVERSION_NONE = "none"
CHINESE_CONVERSION_T2S = "t2s"
CHINESE_CONVERSION_TW2S = "tw2s"
CHINESE_CONVERSION_TW2SP = "tw2sp"

_CONVERSION_LABELS: List[Tuple[str, str]] = [
    (CHINESE_CONVERSION_NONE, "None"),
    (CHINESE_CONVERSION_T2S, "Traditional to Simplified"),
    (CHINESE_CONVERSION_TW2S, "Taiwan Traditional to Simplified"),
    (CHINESE_CONVERSION_TW2SP, "Taiwan Traditional to Simplified with Mainland phrases"),
]

_LABEL_TO_VALUE: Dict[str, str] = {label: value for value, label in _CONVERSION_LABELS}
_SUPPORTED_VALUES = {value for value, _ in _CONVERSION_LABELS}


def get_chinese_conversion_choices() -> List[str]:
    return [label for _, label in _CONVERSION_LABELS]


def normalize_chinese_conversion(raw_value: str | None) -> str:
    if not raw_value:
        return CHINESE_CONVERSION_NONE

    value = raw_value.strip()
    if value in _LABEL_TO_VALUE:
        return _LABEL_TO_VALUE[value]

    normalized = value.lower()
    if normalized in _SUPPORTED_VALUES:
        return normalized

    raise ValueError(
        f"Unsupported Chinese conversion '{raw_value}'. "
        f"Supported values: {sorted(_SUPPORTED_VALUES)}"
    )


def convert_chapters(
    chapters: List[Tuple[str, str]],
    conversion: str | None,
) -> List[Tuple[str, str]]:
    normalized = normalize_chinese_conversion(conversion)
    if normalized == CHINESE_CONVERSION_NONE:
        return chapters

    converter = _build_opencc_converter(normalized)
    return [
        (converter.convert(title), converter.convert(text))
        for title, text in chapters
    ]


def _build_opencc_converter(config_name: str):
    try:
        from opencc import OpenCC
    except ImportError as exc:
        raise ImportError(
            "Chinese conversion requires OpenCC. Install dependencies with "
            "'pip install -r requirements.txt'."
        ) from exc

    return OpenCC(config_name)
