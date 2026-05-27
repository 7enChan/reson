from dataclasses import dataclass
from typing import Dict, List


HEADING_PAUSE_MARKER = " @HEADING_BRK#"
SECTION_BREAK_PAUSE_MARKER = " @SECTION_BRK#"

NARRATION_RHYTHM_CONCISE = "concise"
NARRATION_RHYTHM_NATURAL = "natural"
NARRATION_RHYTHM_MEDITATIVE = "meditative"
NARRATION_RHYTHM_CUSTOM = "custom"

DEFAULT_MINIMAX_NARRATION_RHYTHM = NARRATION_RHYTHM_NATURAL
DEFAULT_MINIMAX_HEADING_PAUSE_SECONDS = 1.2
DEFAULT_MINIMAX_PARAGRAPH_PAUSE_SECONDS = 0.5
DEFAULT_MINIMAX_SECTION_BREAK_PAUSE_SECONDS = 1.8
DEFAULT_MINIMAX_CHAPTER_ENDING_SILENCE_SECONDS = 1.0
MAX_MINIMAX_HEADING_PAUSE_SECONDS = 99.99

_NARRATION_RHYTHM_LABELS = [
    (NARRATION_RHYTHM_CONCISE, "Concise"),
    (NARRATION_RHYTHM_NATURAL, "Natural"),
    (NARRATION_RHYTHM_MEDITATIVE, "Meditative"),
    (NARRATION_RHYTHM_CUSTOM, "Custom"),
]

_RHYTHM_LABEL_TO_VALUE = {
    label: value for value, label in _NARRATION_RHYTHM_LABELS
}
_SUPPORTED_RHYTHMS = {value for value, _ in _NARRATION_RHYTHM_LABELS}

_RHYTHM_PRESETS: Dict[str, Dict[str, float]] = {
    NARRATION_RHYTHM_CONCISE: {
        "heading": 0.8,
        "paragraph": 0.35,
        "section_break": 1.2,
        "chapter_ending": 0.6,
    },
    NARRATION_RHYTHM_NATURAL: {
        "heading": DEFAULT_MINIMAX_HEADING_PAUSE_SECONDS,
        "paragraph": DEFAULT_MINIMAX_PARAGRAPH_PAUSE_SECONDS,
        "section_break": DEFAULT_MINIMAX_SECTION_BREAK_PAUSE_SECONDS,
        "chapter_ending": DEFAULT_MINIMAX_CHAPTER_ENDING_SILENCE_SECONDS,
    },
    NARRATION_RHYTHM_MEDITATIVE: {
        "heading": 1.2,
        "paragraph": 0.65,
        "section_break": 2.0,
        "chapter_ending": 1.2,
    },
}


@dataclass(frozen=True)
class MinimaxNarrationRhythm:
    preset: str
    heading_pause: float
    paragraph_pause: float
    section_break_pause: float
    chapter_ending_silence: float


def get_narration_rhythm_preset_choices() -> List[str]:
    return [label for _, label in _NARRATION_RHYTHM_LABELS]


def get_minimax_narration_preset_values(preset) -> Dict[str, float]:
    normalized = normalize_narration_rhythm_preset(preset)
    if normalized == NARRATION_RHYTHM_CUSTOM:
        normalized = DEFAULT_MINIMAX_NARRATION_RHYTHM
    return dict(_RHYTHM_PRESETS[normalized])


def normalize_narration_rhythm_preset(raw_preset) -> str:
    if not raw_preset:
        return DEFAULT_MINIMAX_NARRATION_RHYTHM

    value = str(raw_preset).strip()
    if value in _RHYTHM_LABEL_TO_VALUE:
        return _RHYTHM_LABEL_TO_VALUE[value]

    normalized = value.lower()
    if normalized in _SUPPORTED_RHYTHMS:
        return normalized

    raise ValueError(
        f"Unsupported narration rhythm preset '{raw_preset}'. "
        f"Supported presets: {sorted(_SUPPORTED_RHYTHMS)}"
    )


def resolve_minimax_narration_rhythm(config) -> MinimaxNarrationRhythm:
    preset = normalize_narration_rhythm_preset(
        getattr(config, "minimax_narration_preset", None)
    )
    defaults = get_minimax_narration_preset_values(preset)

    return MinimaxNarrationRhythm(
        preset=preset,
        heading_pause=resolve_minimax_pause_duration(
            getattr(config, "minimax_heading_pause_duration", None),
            defaults["heading"],
        ),
        paragraph_pause=resolve_minimax_pause_duration(
            getattr(config, "minimax_paragraph_pause_duration", None),
            defaults["paragraph"],
        ),
        section_break_pause=resolve_minimax_pause_duration(
            getattr(config, "minimax_section_break_pause_duration", None),
            defaults["section_break"],
        ),
        chapter_ending_silence=resolve_minimax_pause_duration(
            getattr(config, "minimax_chapter_ending_silence_duration", None),
            defaults["chapter_ending"],
        ),
    )


def resolve_minimax_heading_pause_duration(raw_duration) -> float:
    return resolve_minimax_pause_duration(
        raw_duration,
        DEFAULT_MINIMAX_HEADING_PAUSE_SECONDS,
    )


def resolve_minimax_pause_duration(raw_duration, default_duration: float) -> float:
    if raw_duration is None:
        return default_duration

    try:
        duration = float(raw_duration)
    except (TypeError, ValueError):
        return default_duration

    if duration <= 0:
        return 0.0
    return min(duration, MAX_MINIMAX_HEADING_PAUSE_SECONDS)


def should_insert_minimax_heading_pause(config) -> bool:
    if getattr(config, "tts", None) != "minimax":
        return False
    return resolve_minimax_narration_rhythm(config).heading_pause > 0


def should_insert_minimax_section_break_pause(config) -> bool:
    if getattr(config, "tts", None) != "minimax":
        return False
    return resolve_minimax_narration_rhythm(config).section_break_pause > 0


def format_minimax_pause_marker(duration: float) -> str:
    clamped_duration = resolve_minimax_heading_pause_duration(duration)
    if clamped_duration <= 0:
        return "\n\n"

    formatted = f"{clamped_duration:.2f}".rstrip("0").rstrip(".")
    return f"<#{formatted}#>"
