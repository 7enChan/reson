import logging
import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class M4BChapter:
    title: str
    audio_file: Path


@dataclass(frozen=True)
class M4BChapterTiming:
    title: str
    start_ms: int
    end_ms: int


def export_m4b(
    chapters: Sequence[M4BChapter],
    output_file: Path,
    book_title: str,
    author: str,
    bitrate: str = "96k",
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
) -> Path:
    if not chapters:
        raise ValueError("Cannot export M4B without chapter audio files.")

    ffmpeg = _resolve_binary("ffmpeg", ffmpeg_path)
    ffprobe = _resolve_binary("ffprobe", ffprobe_path)
    resolved_chapters = _validate_chapters(chapters)
    durations_ms = [_probe_duration_ms(ffprobe, chapter.audio_file) for chapter in resolved_chapters]

    output_file.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Exporting single M4B audiobook: %s", output_file)

    with tempfile.TemporaryDirectory(prefix="reson_m4b_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        concat_file = tmp_path / "concat.txt"
        metadata_file = tmp_path / "metadata.txt"
        concat_file.write_text(_build_concat_file(resolved_chapters), encoding="utf-8")
        metadata_file.write_text(
            build_ffmetadata(book_title, author, resolved_chapters, durations_ms),
            encoding="utf-8",
        )

        command = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-f",
            "ffmetadata",
            "-i",
            str(metadata_file),
            "-map",
            "0:a",
            "-map_metadata",
            "1",
            "-map_chapters",
            "1",
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            bitrate,
            "-movflags",
            "+faststart",
            str(output_file),
        ]
        _run(command, "ffmpeg failed while exporting M4B")

    logger.info("M4B export completed: %s", output_file)
    return output_file


def build_ffmetadata(
    book_title: str,
    author: str,
    chapters: Sequence[M4BChapter],
    durations_ms: Sequence[int],
) -> str:
    if len(chapters) != len(durations_ms):
        raise ValueError("Chapter count and duration count must match.")

    lines = [
        ";FFMETADATA1",
        f"title={_escape_ffmetadata_value(book_title)}",
        f"artist={_escape_ffmetadata_value(author)}",
        f"album={_escape_ffmetadata_value(book_title)}",
        "genre=Audiobook",
        "",
    ]

    for timing in _build_chapter_timings(chapters, durations_ms):
        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={timing.start_ms}",
                f"END={timing.end_ms}",
                f"title={_escape_ffmetadata_value(timing.title)}",
                "",
            ]
        )

    return "\n".join(lines)


def _build_chapter_timings(
    chapters: Sequence[M4BChapter],
    durations_ms: Sequence[int],
) -> list[M4BChapterTiming]:
    timings: list[M4BChapterTiming] = []
    cursor_ms = 0
    for chapter, duration_ms in zip(chapters, durations_ms):
        end_ms = cursor_ms + duration_ms
        timings.append(M4BChapterTiming(chapter.title, cursor_ms, end_ms))
        cursor_ms = end_ms
    return timings


def _validate_chapters(chapters: Sequence[M4BChapter]) -> list[M4BChapter]:
    resolved: list[M4BChapter] = []
    for chapter in chapters:
        audio_file = Path(chapter.audio_file)
        if not audio_file.is_file():
            raise FileNotFoundError(f"Chapter audio file not found: {audio_file}")
        resolved.append(M4BChapter(chapter.title, audio_file.resolve()))
    return resolved


def _resolve_binary(binary_name: str, explicit_path: str | None) -> str:
    if explicit_path:
        return explicit_path

    resolved = shutil.which(binary_name)
    if not resolved:
        raise FileNotFoundError(
            f"{binary_name} is required for M4B export but was not found in PATH."
        )
    return resolved


def _probe_duration_ms(ffprobe: str, audio_file: Path) -> int:
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_file),
    ]
    result = _run(command, f"ffprobe failed while reading duration: {audio_file}")
    duration_seconds = float(result.stdout.strip())
    duration_ms = math.ceil(duration_seconds * 1000)
    if duration_ms <= 0:
        raise ValueError(f"Invalid chapter duration for M4B export: {audio_file}")
    return duration_ms


def _run(command: Sequence[str], error_message: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(command),
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        logger.error("%s. stderr: %s", error_message, stderr)
        raise RuntimeError(f"{error_message}. {stderr}") from exc


def _build_concat_file(chapters: Sequence[M4BChapter]) -> str:
    lines = ["ffconcat version 1.0"]
    lines.extend(f"file {_quote_concat_path(chapter.audio_file)}" for chapter in chapters)
    return "\n".join(lines) + "\n"


def _quote_concat_path(path: Path) -> str:
    escaped = str(path).replace("\\", "\\\\").replace("'", "'\\''")
    return f"'{escaped}'"


def _escape_ffmetadata_value(value: str) -> str:
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("=", "\\=")
        .replace(";", "\\;")
        .replace("#", "\\#")
    )
