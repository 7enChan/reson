#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from audiobook_generator.book_parsers.epub_book_parser import EpubBookParser
from audiobook_generator.utils.chinese_conversion import convert_chapters


AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".m4b", ".opus", ".flac"}
NUMBERED_AUDIO_PATTERN = re.compile(r"^\d+_.+")


def build_config(input_file, mode):
    return SimpleNamespace(
        input_file=str(input_file),
        title_mode="first_few" if mode == "first_few" else "auto",
        newline_mode="double",
        remove_endnotes=False,
        remove_reference_numbers=False,
        search_and_replace_file=None,
        tts="edge",
        minimax_narration_preset=None,
        minimax_heading_pause_duration=0,
        minimax_paragraph_pause_duration=None,
        minimax_section_break_pause_duration=0,
        minimax_chapter_ending_silence_duration=None,
    )


def get_titles(input_file, mode, chinese_conversion):
    parser = EpubBookParser(build_config(input_file, mode))
    if mode == "document":
        chapters = parser._get_document_chapters(" @BRK#")
    else:
        chapters = parser.get_chapters(" @BRK#")

    chapters = [(title, text) for title, text in chapters if text.strip()]
    chapters = convert_chapters(chapters, chinese_conversion)
    return [title for title, _ in chapters]


def get_audio_files(output_dir):
    files = [
        path
        for path in output_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() in AUDIO_EXTENSIONS
        and NUMBERED_AUDIO_PATTERN.match(path.name)
    ]
    return sorted(files, key=lambda path: path.name)


def build_plan(audio_files, titles):
    if len(audio_files) != len(titles):
        raise ValueError(
            f"Output file count ({len(audio_files)}) does not match title count ({len(titles)})."
        )

    plan = []
    for index, (source, title) in enumerate(zip(audio_files, titles)):
        target = source.with_name(f"{index:03d}_{title}{source.suffix}")
        plan.append((source, target))
    return plan


def validate_plan(plan):
    sources = {source.resolve() for source, _ in plan}
    targets = [target.resolve() for _, target in plan]
    duplicate_targets = {
        target
        for target in targets
        if targets.count(target) > 1
    }
    if duplicate_targets:
        duplicates = "\n".join(str(path) for path in sorted(duplicate_targets))
        raise ValueError(f"Duplicate target names:\n{duplicates}")

    for _, target in plan:
        if target.exists() and target.resolve() not in sources:
            raise FileExistsError(f"Target already exists and is not part of this rename: {target}")


def apply_plan(plan):
    temp_plan = []
    for index, (source, target) in enumerate(plan):
        temp = source.with_name(f".{source.name}.rename-tmp-{index}")
        source.rename(temp)
        temp_plan.append((temp, target))

    for temp, target in temp_plan:
        temp.rename(target)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Rename generated audiobook files using EPUB-derived chapter titles."
    )
    parser.add_argument("input_file", help="Source EPUB used to generate the audiobook.")
    parser.add_argument("output_dir", help="Generated audiobook output directory.")
    parser.add_argument(
        "--mode",
        choices=["document", "toc"],
        default="document",
        help=(
            "document: match already-generated file-per-XHTML output. "
            "toc: match new TOC-anchor chapter output."
        ),
    )
    parser.add_argument(
        "--chinese_conversion",
        default="none",
        help="Apply the same Chinese conversion used during generation, e.g. tw2s or tw2sp.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the rename. Without this flag, only prints a dry run.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    input_file = Path(args.input_file)
    output_dir = Path(args.output_dir)

    titles = get_titles(input_file, args.mode, args.chinese_conversion)
    audio_files = get_audio_files(output_dir)
    plan = build_plan(audio_files, titles)
    validate_plan(plan)

    for source, target in plan:
        if source.name != target.name:
            print(f"{source.name} -> {target.name}")

    if args.apply:
        apply_plan(plan)
        print(f"Renamed {len(plan)} files.")
    else:
        print(f"Dry run only. Add --apply to rename {len(plan)} files.")


if __name__ == "__main__":
    main()
