import io
import logging
import math
import os
import time
from typing import List, Optional

import requests

try:
    import fal_client  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    fal_client = None

from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.core.audio_tags import AudioTags
from audiobook_generator.tts_providers.base_tts_provider import BaseTTSProvider
from audiobook_generator.utils.utils import (
    merge_audio_segments,
    set_audio_tags,
    split_text,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "fal-ai/minimax/speech-02-hd"
DEFAULT_VOICE = "Chinese (Mandarin)_Warm_Bestie"
DEFAULT_OUTPUT_FORMAT = "mp3"
DEFAULT_BREAK_STRING = " @BRK#"
DEFAULT_MAX_INPUT_CHARS = 4500  # Conservative limit (API max is 5000)
DEFAULT_TIMEOUT_SECONDS = 60
MAX_RETRIES = 4
RETRY_BACKOFF_SECONDS = 2
# MiniMax pricing: Estimated at $0.015 per 1000 characters (placeholder - adjust based on actual pricing)
USD_PER_1000_CHAR = 0.015

_SUPPORTED_VOICES = [
    "Chinese (Mandarin)_Warm_Bestie",
    "Chinese (Mandarin)_Sincere_Adult",
    "Chinese (Mandarin)_Soft_Girl",
]

_SUPPORTED_LANGUAGE_BOOSTS = [
    "Chinese",
    "Chinese,Yue",
    "English",
    "Arabic",
    "Russian",
    "Spanish",
    "French",
    "Portuguese",
    "German",
    "Turkish",
    "Dutch",
    "Ukrainian",
    "Vietnamese",
    "Indonesian",
    "Japanese",
    "Italian",
    "Korean",
    "Thai",
    "Polish",
    "Romanian",
    "Greek",
    "Czech",
    "Finnish",
    "Hindi",
    "Bulgarian",
    "Danish",
    "Hebrew",
    "Malay",
    "Slovak",
    "Swedish",
    "Croatian",
    "Hungarian",
    "Norwegian",
    "Slovenian",
    "Catalan",
    "Nynorsk",
    "Afrikaans",
    "auto",
]

_LANGUAGE_BOOST_MAPPING = {
    "zh": "Chinese",
    "zh-cn": "Chinese",
    "zh-tw": "Chinese,Yue",
    "zh-hk": "Chinese,Yue",
    "en": "English",
    "en-us": "English",
    "en-gb": "English",
    "ar": "Arabic",
    "ru": "Russian",
    "es": "Spanish",
    "fr": "French",
    "pt": "Portuguese",
    "de": "German",
    "tr": "Turkish",
    "nl": "Dutch",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "ja": "Japanese",
    "it": "Italian",
    "ko": "Korean",
    "th": "Thai",
    "pl": "Polish",
    "ro": "Romanian",
    "el": "Greek",
    "cs": "Czech",
    "fi": "Finnish",
    "hi": "Hindi",
    "bg": "Bulgarian",
    "da": "Danish",
    "he": "Hebrew",
    "ms": "Malay",
    "sk": "Slovak",
    "sv": "Swedish",
    "hr": "Croatian",
    "hu": "Hungarian",
    "no": "Norwegian",
    "sl": "Slovenian",
    "ca": "Catalan",
    "af": "Afrikaans",
}


def get_minimax_supported_voices() -> List[str]:
    return list(_SUPPORTED_VOICES)


def get_minimax_supported_language_boosts() -> List[str]:
    return list(_SUPPORTED_LANGUAGE_BOOSTS)


class MinimaxTTSProvider(BaseTTSProvider):
    def __init__(self, config: GeneralConfig):
        config.model_name = config.model_name or DEFAULT_MODEL
        config.voice_name = config.voice_name or DEFAULT_VOICE
        config.output_format = (config.output_format or DEFAULT_OUTPUT_FORMAT).lower()
        config.language = config.language or "en-US"

        self._speed = self._resolve_speed(config.minimax_speed)
        self._volume = self._resolve_volume(config.minimax_volume)
        self._pitch = self._resolve_pitch(config.minimax_pitch)
        self._language_boost = self._resolve_language_boost(
            config.minimax_language_boost,
            config.language,
        )
        self._timeout = self._resolve_timeout(config.minimax_request_timeout)
        self.price = USD_PER_1000_CHAR
        self._max_chars = DEFAULT_MAX_INPUT_CHARS

        self._api_key = config.minimax_api_key or os.environ.get("FAL_KEY")
        if not self._api_key:
            raise ValueError(
                "MinimaxTTSProvider: FAL_KEY environment variable or --minimax_api_key is required."
            )

        if fal_client is None:
            raise ImportError(
                "MinimaxTTSProvider: fal-client is required. Install it via 'pip install fal-client'."
            )

        # Configure fal_client with API key
        os.environ["FAL_KEY"] = self._api_key

        super().__init__(config)

    def __str__(self) -> str:
        return (
            f"MinimaxTTSProvider(model={self.config.model_name}, voice={self.config.voice_name}, "
            f"speed={self._speed}, volume={self._volume}, pitch={self._pitch}, "
            f"language_boost={self._language_boost}, output_format={self.config.output_format})"
        )

    def validate_config(self):
        if self.config.voice_name not in _SUPPORTED_VOICES:
            raise ValueError(
                f"MinimaxTTS: Unsupported voice '{self.config.voice_name}'. Supported voices: {_SUPPORTED_VOICES}"
            )
        if self._language_boost and self._language_boost not in _SUPPORTED_LANGUAGE_BOOSTS:
            raise ValueError(
                f"MinimaxTTS: Unsupported language boost '{self._language_boost}'. "
                f"Supported options: {_SUPPORTED_LANGUAGE_BOOSTS}"
            )
        if self.config.output_format not in ["mp3", "wav"]:
            raise ValueError(
                "MinimaxTTS: Only 'mp3' and 'wav' output formats are supported. "
                "Please set --output_format mp3 or --output_format wav."
            )

    def text_to_speech(self, text: str, output_file: str, audio_tags: AudioTags):
        if not text.strip():
            logger.warning("MinimaxTTS: Empty text received; skipping chunk synthesis.")
            return

        chunks = split_text(text, self._max_chars, self.config.language)
        audio_segments: List[io.BytesIO] = []
        chunk_ids: List[str] = []

        for index, chunk in enumerate(chunks, 1):
            chunk_id = f"chapter-{audio_tags.idx}_{audio_tags.title}_chunk_{index}_of_{len(chunks)}"
            logger.info("MinimaxTTS: Processing %s (length=%s)", chunk_id, len(chunk))
            prepared_text = self._prepare_text(chunk)

            segment = self._synthesize_with_retry(prepared_text, chunk_id)
            audio_segments.append(segment)
            chunk_ids.append(chunk_id)

        merge_audio_segments(
            audio_segments,
            output_file,
            self.get_output_file_extension(),
            chunk_ids,
            True,  # ensure audio data is normalized via pydub
        )
        set_audio_tags(output_file, audio_tags)

    def estimate_cost(self, total_chars: int) -> float:
        return math.ceil(total_chars / 1000) * self.price

    def get_break_string(self):
        return DEFAULT_BREAK_STRING

    def get_output_file_extension(self):
        return self.config.output_format

    def _prepare_text(self, text: str) -> str:
        return text.replace(self.get_break_string(), "\n\n").strip()

    def _synthesize_with_retry(self, text: str, chunk_id: str) -> io.BytesIO:
        last_error: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self._synthesize(text)
            except Exception as exc:  # pragma: no cover - network interaction
                last_error = exc
                logger.warning(
                    "MinimaxTTS: Attempt %s/%s failed for %s due to %s", attempt, MAX_RETRIES, chunk_id, exc
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
        logger.error("MinimaxTTS: Exhausted retries for %s", chunk_id)
        if last_error:
            raise last_error
        raise RuntimeError(f"MinimaxTTS: Failed to synthesize chunk {chunk_id}")

    def _synthesize(self, text: str) -> io.BytesIO:
        arguments = {
            "text": text,
            "voice_setting": {
                "speed": self._speed,
                "vol": self._volume,
                "voice_id": self.config.voice_name,
                "pitch": self._pitch,
                "english_normalization": False,
            },
            "output_format": "url",  # Always use URL format for easier download
        }

        if self._language_boost:
            arguments["language_boost"] = self._language_boost

        logger.debug("MinimaxTTS: Calling API with arguments: %s", arguments)

        response = fal_client.subscribe(
            self.config.model_name,
            arguments=arguments,
            with_logs=False,
        )

        audio_url = response.get("audio", {}).get("url")
        if not audio_url:
            raise RuntimeError("MinimaxTTS: Response did not contain an audio URL.")

        logger.debug("MinimaxTTS: Downloading audio from %s", audio_url)
        audio_bytes = self._download_audio(audio_url)
        buffer = io.BytesIO(audio_bytes)
        buffer.seek(0)
        return buffer

    def _download_audio(self, url: str) -> bytes:
        response = requests.get(url, timeout=self._timeout)
        response.raise_for_status()
        return response.content

    @staticmethod
    def _resolve_speed(raw_speed: Optional[float]) -> float:
        """Resolve speed parameter (default: 1.0, range typically 0.5-2.0)"""
        if raw_speed is None:
            return 1.0
        try:
            speed = float(raw_speed)
            return max(0.5, min(2.0, speed))
        except (ValueError, TypeError):
            return 1.0

    @staticmethod
    def _resolve_volume(raw_volume: Optional[float]) -> float:
        """Resolve volume parameter (default: 1.0, range typically 0.1-2.0)"""
        if raw_volume is None:
            return 1.0
        try:
            volume = float(raw_volume)
            return max(0.1, min(2.0, volume))
        except (ValueError, TypeError):
            return 1.0

    @staticmethod
    def _resolve_pitch(raw_pitch: Optional[float]) -> float:
        """Resolve pitch parameter (default: 0, range typically -12 to 12)"""
        if raw_pitch is None:
            return 0.0
        try:
            pitch = float(raw_pitch)
            return max(-12.0, min(12.0, pitch))
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _resolve_timeout(raw_timeout: Optional[int]) -> int:
        try:
            timeout = int(raw_timeout) if raw_timeout is not None else DEFAULT_TIMEOUT_SECONDS
            if timeout <= 0:
                raise ValueError
            return timeout
        except (ValueError, TypeError):
            return DEFAULT_TIMEOUT_SECONDS

    @staticmethod
    def _resolve_language_boost(explicit: Optional[str], locale: Optional[str]) -> Optional[str]:
        """Resolve language_boost from explicit setting or locale"""
        if explicit:
            return explicit
        if not locale:
            return None
        normalized = locale.lower()
        return _LANGUAGE_BOOST_MAPPING.get(normalized)
