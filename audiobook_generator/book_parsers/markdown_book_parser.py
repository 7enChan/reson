import logging
import os
import re
from typing import Dict, List, Optional, Tuple

from audiobook_generator.book_parsers.base_book_parser import BaseBookParser
from audiobook_generator.config.general_config import GeneralConfig

logger = logging.getLogger(__name__)


class MarkdownBookParser(BaseBookParser):
    FRONT_MATTER_DELIMITER = re.compile(r"^---\s*$")
    METADATA_PATTERN = re.compile(r"^(?P<key>[A-Za-z0-9_\- ]+):\s*(?P<value>.+)$")
    HEADING_PATTERN = re.compile(r"^\s*(#{1,6})\s+(.*)$")

    def __init__(self, config: GeneralConfig):
        super().__init__(config)
        self.raw_text = self._read_file()
        self.metadata, self.body_lines = self._extract_front_matter(self.raw_text)

    def __str__(self) -> str:
        return super().__str__()

    def validate_config(self):
        if not self.config.input_file:
            raise ValueError("Markdown Parser: Input file cannot be empty")
        if not self.config.input_file.endswith((".md", ".markdown")):
            raise ValueError(
                f"Markdown Parser: Unsupported file format: {self.config.input_file}"
            )
        if not os.path.exists(self.config.input_file):
            raise FileNotFoundError(
                f"Markdown Parser: Input file not found: {self.config.input_file}"
            )

    def get_book(self):
        return self.raw_text

    def get_book_title(self) -> str:
        if "title" in self.metadata:
            return self.metadata["title"]

        for line in self.body_lines:
            heading_match = self.HEADING_PATTERN.match(line)
            if heading_match and len(heading_match.group(1)) == 1:
                return heading_match.group(2).strip()

        return os.path.splitext(os.path.basename(self.config.input_file))[0]

    def get_book_author(self) -> str:
        for key in ("author", "authors", "creator"):
            if key in self.metadata:
                return self.metadata[key]
        return "Unknown"

    def get_chapters(self, break_string) -> List[Tuple[str, str]]:
        chapters: List[Tuple[str, str]] = []
        search_and_replaces = self.get_search_and_replaces()
        current_title: Optional[str] = None
        current_lines: List[str] = []
        fallback_index = 1

        for line in self.body_lines:
            heading_match = self.HEADING_PATTERN.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                if level <= 2:
                    if current_title is not None or current_lines:
                        chapter_text = self._build_chapter_text(
                            current_lines,
                            break_string,
                            search_and_replaces,
                            current_title,
                        )
                        if chapter_text:
                            title_source = current_title or f"Chapter {fallback_index}"
                            sanitized_title = self.sanitize_title(
                                title_source, break_string
                            )
                            chapters.append((sanitized_title, chapter_text))
                            fallback_index += 1
                    current_title = heading_text
                    current_lines = []
                    continue
            current_lines.append(line)

        if current_title is not None or current_lines:
            chapter_text = self._build_chapter_text(
                current_lines,
                break_string,
                search_and_replaces,
                current_title,
            )
            if chapter_text:
                title_source = current_title or f"Chapter {fallback_index}"
                sanitized_title = self.sanitize_title(title_source, break_string)
                chapters.append((sanitized_title, chapter_text))

        if not chapters and self.body_lines:
            text = self._build_chapter_text(
                self.body_lines,
                break_string,
                search_and_replaces,
                self.get_book_title(),
            )
            if text:
                title_source = self.get_book_title() or "Chapter 1"
                sanitized_title = self.sanitize_title(title_source, break_string)
                chapters.append((sanitized_title, text))

        return chapters

    def get_search_and_replaces(self):
        search_and_replaces = []
        if self.config.search_and_replace_file:
            with open(self.config.search_and_replace_file) as fp:
                search_and_replace_content = fp.readlines()
                for search_and_replace in search_and_replace_content:
                    if (
                        "==" in search_and_replace
                        and not search_and_replace.startswith("==")
                        and not search_and_replace.endswith("==")
                        and not search_and_replace.startswith("#")
                    ):
                        search = search_and_replace.split("==")[0]
                        replace = search_and_replace.split("==")[1][:-1]
                        search_and_replaces.append(
                            {"search": rf"{search}", "replace": rf"{replace}"}
                        )
        return search_and_replaces

    def _read_file(self) -> str:
        with open(self.config.input_file, "r", encoding="utf-8") as fp:
            return fp.read()

    def _extract_front_matter(self, text: str) -> Tuple[Dict[str, str], List[str]]:
        lines = text.splitlines()
        metadata: Dict[str, str] = {}
        body_start = 0

        if lines and self.FRONT_MATTER_DELIMITER.match(lines[0]):
            for idx in range(1, len(lines)):
                if self.FRONT_MATTER_DELIMITER.match(lines[idx]):
                    body_start = idx + 1
                    break
                meta_match = self.METADATA_PATTERN.match(lines[idx])
                if meta_match:
                    key = meta_match.group("key").strip().lower()
                    value = meta_match.group("value").strip()
                    metadata[key] = value
        else:
            body_start = 0

        body_lines = lines[body_start:]
        return metadata, body_lines

    def _build_chapter_text(
        self,
        lines: List[str],
        break_string: str,
        search_and_replaces: List[Dict[str, str]],
        heading: Optional[str] = None,
    ) -> str:
        if not lines and not heading:
            return ""

        parts: List[str] = []
        if heading:
            heading_text = heading.strip()
            if heading_text:
                parts.append(heading_text)
        if lines:
            body_text = "\n".join(lines).strip()
            if body_text:
                parts.append(body_text)

        text = "\n\n".join(parts).strip()
        if not text:
            return ""

        text = self._strip_markdown(text)
        text = self._apply_newline_mode(text, break_string)

        if self.config.remove_endnotes:
            text = re.sub(r'(?<=[a-zA-Z.,!?;\"”)])\d+', "", text)
        if self.config.remove_reference_numbers:
            text = re.sub(r'\[\d+(\.\d+)?\]', "", text)

        for search_and_replace in search_and_replaces:
            text = re.sub(
                search_and_replace["search"],
                search_and_replace["replace"],
                text,
            )

        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _apply_newline_mode(self, text: str, break_string: str) -> str:
        text = text.replace("\r\n", "\n")
        if self.config.newline_mode == "single":
            cleaned = re.sub(r"\n+", f" {break_string.strip()} ", text)
        elif self.config.newline_mode == "double":
            cleaned = re.sub(r"\n{2,}", f" {break_string.strip()} ", text)
            cleaned = re.sub(r"\n", " ", cleaned)
        elif self.config.newline_mode == "none":
            cleaned = re.sub(r"\n", " ", text)
        else:
            raise ValueError(f"Invalid newline mode: {self.config.newline_mode}")
        return cleaned

    def _strip_markdown(self, text: str) -> str:
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)  # remove code blocks
        text = re.sub(r"`([^`]*)`", r"\1", text)  # inline code
        text = re.sub(r"!\[([^\]]*)\]\([^\)]*\)", r"\1", text)  # images
        text = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)  # links
        text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)  # bold
        text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)  # italic
        text = re.sub(r"^>+\s?", "", text, flags=re.MULTILINE)  # blockquotes
        text = re.sub(r"^\s{0,3}[-*+]\s+", "", text, flags=re.MULTILINE)  # bullet list
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)  # numbered list
        text = re.sub(r"^\s*(#{1,6})\s*", "", text, flags=re.MULTILINE)  # headings
        return text
