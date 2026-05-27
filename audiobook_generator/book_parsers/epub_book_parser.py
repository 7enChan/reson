import copy
import logging
import posixpath
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote, urldefrag

import ebooklib
from bs4 import BeautifulSoup, NavigableString
from ebooklib import epub

from audiobook_generator.book_parsers.base_book_parser import BaseBookParser
from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.utils.heading_pause import (
    HEADING_PAUSE_MARKER,
    SECTION_BREAK_PAUSE_MARKER,
    should_insert_minimax_heading_pause,
    should_insert_minimax_section_break_pause,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TocEntry:
    title: str
    document_name: str
    fragment: Optional[str]


class EpubBookParser(BaseBookParser):
    SECTION_BREAK_PATTERN = re.compile(r"^\s*([*\-—_·・※＊]\s*){3,}$")

    def __init__(self, config: GeneralConfig):
        super().__init__(config)
        self.book = epub.read_epub(self.config.input_file, {"ignore_ncx": True})

    def __str__(self) -> str:
        return super().__str__()

    def validate_config(self):
        if self.config.input_file is None:
            raise ValueError("Epub Parser: Input file cannot be empty")
        if not self.config.input_file.endswith(".epub"):
            raise ValueError(f"Epub Parser: Unsupported file format: {self.config.input_file}")

    def get_book(self):
        return self.book

    def get_book_title(self) -> str:
        if self.book.get_metadata('DC', 'title'):
            return self.book.get_metadata("DC", "title")[0][0]
        return "Untitled"

    def get_book_author(self) -> str:
        if self.book.get_metadata('DC', 'creator'):
            return self.book.get_metadata("DC", "creator")[0][0]
        return "Unknown"

    def get_chapters(self, break_string) -> List[Tuple[str, str]]:
        search_and_replaces = self.get_search_and_replaces()
        if self.config.title_mode == "auto":
            toc_chapters = self._get_toc_chapters(break_string, search_and_replaces)
            if toc_chapters:
                return toc_chapters
        return self._get_document_chapters(break_string, search_and_replaces)

    def _get_document_chapters(
        self,
        break_string,
        search_and_replaces=None,
    ) -> List[Tuple[str, str]]:
        chapters = []
        search_and_replaces = search_and_replaces or []
        for item in self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = self._prepare_soup(item.get_content())
            raw = soup.get_text(strip=False)
            logger.debug(f"Raw text: <{raw[:]}>")

            cleaned_text = self._clean_text(raw, break_string, search_and_replaces)
            logger.debug(f"Cleaned text step 5: <{cleaned_text[:100]}>")

            # Get proper chapter title
            if self.config.title_mode == "auto":
                title = self._extract_document_title(soup)
                if not title:
                    title = cleaned_text[:60]
            elif self.config.title_mode == "tag_text":
                title = self._extract_document_title(soup)
                if not title:
                    title = "<blank>"
            elif self.config.title_mode == "first_few":
                title = cleaned_text[:60]
            else:
                raise ValueError("Unsupported title_mode")
            logger.debug(f"Raw title: <{title}>")
            title = self.sanitize_title(title, break_string)
            logger.debug(f"Sanitized title: <{title}>")

            chapters.append((title, cleaned_text))
            soup.decompose()
        return chapters

    def _get_toc_chapters(
        self,
        break_string,
        search_and_replaces,
    ) -> List[Tuple[str, str]]:
        toc_entries = self._flatten_toc_entries(self.book.toc)
        if not toc_entries:
            return []

        document_items = {
            item.get_name(): item
            for item in self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
        }
        prepared_soups: Dict[str, BeautifulSoup] = {}
        chapters: List[Tuple[str, str]] = []

        for index, toc_entry in enumerate(toc_entries):
            item = document_items.get(toc_entry.document_name)
            if item is None:
                continue

            if toc_entry.document_name not in prepared_soups:
                prepared_soups[toc_entry.document_name] = self._prepare_soup(
                    item.get_content()
                )

            end_fragment = self._next_toc_fragment_in_document(
                toc_entries,
                index,
                toc_entry.document_name,
            )
            raw = self._extract_segment_text(
                prepared_soups[toc_entry.document_name],
                toc_entry.fragment,
                end_fragment,
            )
            cleaned_text = self._clean_text(raw, break_string, search_and_replaces)
            if not cleaned_text.strip():
                continue

            title = self.sanitize_title(toc_entry.title, break_string)
            logger.debug(f"TOC title: <{toc_entry.title}> -> <{title}>")
            chapters.append((title, cleaned_text))

        for soup in prepared_soups.values():
            soup.decompose()
        return chapters

    def _prepare_soup(self, content) -> BeautifulSoup:
        soup = BeautifulSoup(content, "lxml-xml")
        if should_insert_minimax_heading_pause(self.config):
            self._insert_heading_pause_markers(soup)
        if should_insert_minimax_section_break_pause(self.config):
            self._insert_section_break_pause_markers(soup)
        return soup

    def _clean_text(self, raw, break_string, search_and_replaces) -> str:
        # Replace excessive whitespaces and newline characters based on the mode
        if self.config.newline_mode == "single":
            cleaned_text = re.sub(r"[\n]+", break_string, raw.strip())
        elif self.config.newline_mode == "double":
            cleaned_text = re.sub(r"[\n]{2,}", break_string, raw.strip())
        elif self.config.newline_mode == "none":
            cleaned_text = re.sub(r"[\n]+", " ", raw.strip())
        else:
            raise ValueError(f"Invalid newline mode: {self.config.newline_mode}")

        logger.debug(f"Cleaned text step 1: <{cleaned_text[:]}>")
        cleaned_text = re.sub(r"\s+", " ", cleaned_text)
        logger.debug(f"Cleaned text step 2: <{cleaned_text[:100]}>")

        # Removes end-note numbers
        if self.config.remove_endnotes:
            cleaned_text = re.sub(r'(?<=[a-zA-Z.,!?;”")])\d+', "", cleaned_text)
            logger.debug(f"Cleaned text step 4: <{cleaned_text[:100]}>")

        # Removes references numbers like [1] or [2.3]
        if self.config.remove_reference_numbers:
            cleaned_text = re.sub(r'\[\d+(\.\d+)?\]', '', cleaned_text)
            logger.debug(f"Cleaned text step 4.1 (removed brackets): <{cleaned_text[:100]}>")

        # Does user defined search and replaces
        for search_and_replace in search_and_replaces:
            cleaned_text = re.sub(search_and_replace['search'], search_and_replace['replace'], cleaned_text)
        return cleaned_text

    def _extract_document_title(self, soup: BeautifulSoup) -> str:
        title_levels = ["title", "h1", "h2", "h3", "h4", "h5", "h6", "legend"]
        headings = [
            tag.get_text(" ", strip=True)
            for tag in soup.find_all(title_levels)
            if tag.get_text(" ", strip=True)
        ]
        if not headings:
            return ""
        if re.match(r"^\d{1,4}$", headings[0]):
            if len(headings) > 1:
                return f"{headings[0]} {headings[1]}"
            return ""
        return headings[0]

    def _flatten_toc_entries(self, toc_items) -> List[TocEntry]:
        toc_entries: List[TocEntry] = []
        for item in toc_items:
            if isinstance(item, tuple):
                toc_entries.extend(self._flatten_toc_entries([item[0]]))
                toc_entries.extend(self._flatten_toc_entries(item[1]))
                continue

            title = getattr(item, "title", None)
            href = getattr(item, "href", None)
            if not title or not href:
                continue

            document_name, fragment = self._parse_toc_href(href)
            if not document_name:
                continue
            toc_entries.append(TocEntry(title, document_name, fragment))
        return toc_entries

    @staticmethod
    def _parse_toc_href(href: str) -> Tuple[str, Optional[str]]:
        document_name, fragment = urldefrag(href)
        document_name = posixpath.normpath(unquote(document_name)).lstrip("/")
        fragment = unquote(fragment) if fragment else None
        return document_name, fragment

    @staticmethod
    def _next_toc_fragment_in_document(
        toc_entries: List[TocEntry],
        current_index: int,
        document_name: str,
    ) -> Optional[str]:
        for next_entry in toc_entries[current_index + 1:]:
            if next_entry.document_name == document_name:
                return next_entry.fragment
            if next_entry.document_name != document_name:
                return None
        return None

    def _extract_segment_text(
        self,
        soup: BeautifulSoup,
        start_fragment: Optional[str],
        end_fragment: Optional[str],
    ) -> str:
        working_soup = copy.deepcopy(soup)
        start_marker = "__AUDIOBOOK_SEGMENT_START__"
        end_marker = "__AUDIOBOOK_SEGMENT_END__"

        if start_fragment:
            start_node = self._find_fragment_node(working_soup, start_fragment)
            if start_node is None:
                logger.debug("TOC fragment not found: %s", start_fragment)
                working_soup.decompose()
                return ""
            start_node.insert_before(NavigableString(start_marker))
        else:
            body = working_soup.find("body") or working_soup
            body.insert(0, NavigableString(start_marker))

        has_end_marker = False
        if end_fragment and end_fragment != start_fragment:
            end_node = self._find_fragment_node(working_soup, end_fragment)
            if end_node is not None:
                end_node.insert_before(NavigableString(end_marker))
                has_end_marker = True

        raw = working_soup.get_text(strip=False)
        working_soup.decompose()
        if start_marker not in raw:
            return ""
        segment = raw.split(start_marker, 1)[1]
        if has_end_marker and end_marker in segment:
            segment = segment.split(end_marker, 1)[0]
        return segment

    @staticmethod
    def _find_fragment_node(soup: BeautifulSoup, fragment: str):
        return soup.find(id=fragment) or soup.find(attrs={"name": fragment})

    def _insert_heading_pause_markers(self, soup: BeautifulSoup):
        marker = f" {HEADING_PAUSE_MARKER.strip()} "
        for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
            if heading.get_text(strip=True):
                heading.insert_after(NavigableString(marker))

    def _insert_section_break_pause_markers(self, soup: BeautifulSoup):
        marker = f" {SECTION_BREAK_PAUSE_MARKER.strip()} "
        for separator in soup.find_all("hr"):
            separator.insert_after(NavigableString(marker))

        for block in soup.find_all(["p", "div"]):
            text = block.get_text(" ", strip=True)
            if self._is_section_break_text(text):
                block.clear()
                block.append(NavigableString(marker))

    def _is_section_break_text(self, text: str) -> bool:
        return bool(self.SECTION_BREAK_PATTERN.match(text or ""))

    def get_search_and_replaces(self):
        search_and_replaces = []
        if self.config.search_and_replace_file:
            with open(self.config.search_and_replace_file) as fp:
                search_and_replace_content = fp.readlines()
                for search_and_replace in search_and_replace_content:
                    if '==' in search_and_replace and not search_and_replace.startswith('==') and not search_and_replace.endswith('==') and not search_and_replace.startswith('#'):
                        search_and_replaces = search_and_replaces + [ {'search': r"{}".format(search_and_replace.split('==')[0]), 'replace': r"{}".format(search_and_replace.split('==')[1][:-1])} ]
        return search_and_replaces
