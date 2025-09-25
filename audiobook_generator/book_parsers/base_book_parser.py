from typing import List, Tuple

import re

from audiobook_generator.config.general_config import GeneralConfig

EPUB = "epub"
MARKDOWN = "markdown"


class BaseBookParser:  # Base interface for books parsers
    # Base Book Parser interface
    def __init__(self, config: GeneralConfig):
        self.config = config
        self.validate_config()

    def __str__(self) -> str:
        return f"{self.config}"

    def validate_config(self):
        raise NotImplementedError

    def get_book(self):
        raise NotImplementedError

    def get_book_title(self) -> str:
        raise NotImplementedError

    def get_book_author(self) -> str:
        raise NotImplementedError

    def get_chapters(self, break_string) -> List[Tuple[str, str]]:
        raise NotImplementedError

    @staticmethod
    def sanitize_title(title: str, break_string: str) -> str:
        """Prepare chapter titles for use in file names and ID3 tags."""
        title = title.replace(break_string, " ")
        sanitized_title = re.sub(r"[^\w\s]", "", title, flags=re.UNICODE)
        sanitized_title = re.sub(r"\s+", "_", sanitized_title.strip())
        if not sanitized_title:
            sanitized_title = "chapter"
        return sanitized_title


# Common support methods for all book parsers

def get_supported_book_parsers() -> List[str]:
    return [EPUB, MARKDOWN]


def get_book_parser(config) -> BaseBookParser:
    if config.input_file.endswith(EPUB):
        from audiobook_generator.book_parsers.epub_book_parser import EpubBookParser
        return EpubBookParser(config)
    elif config.input_file.endswith((".md", ".markdown")):
        from audiobook_generator.book_parsers.markdown_book_parser import MarkdownBookParser

        return MarkdownBookParser(config)
    # elif <- new book parser goes here
    else:
        raise NotImplementedError(f"Unsupported file format: {config.input_file}")
