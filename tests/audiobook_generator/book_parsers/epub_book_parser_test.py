import unittest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

from bs4 import BeautifulSoup
from ebooklib import epub

from audiobook_generator.book_parsers.base_book_parser import get_book_parser
from audiobook_generator.book_parsers.epub_book_parser import EpubBookParser
from audiobook_generator.utils.heading_pause import (
    HEADING_PAUSE_MARKER,
    SECTION_BREAK_PAUSE_MARKER,
)
from tests.test_utils import get_azure_config


class TestGetBookParser(unittest.TestCase):

    def test_get_epub_book_parser(self):
        # Create a config object with the path to an actual EPUB file
        config = get_azure_config()

        # Call get_book_parser and assert the correct parser is returned
        parser = get_book_parser(config)
        self.assertIsInstance(parser, EpubBookParser)
        self.assertEqual(parser.get_book_author(), "Daniel Defoe")
        self.assertEqual(parser.get_book_title(), "The Life and Adventures of Robinson Crusoe")
        self.assertEqual(parser.sanitize_title(parser.get_book_title(), " @BRK#"), "The Life and Adventures of Robinson Crusoe")
        self.assertEqual(len(parser.get_chapters("   ")), 24)

    def test_auto_title_mode_uses_toc_anchors_as_chapter_boundaries(self):
        with TemporaryDirectory() as temp_dir:
            epub_path = f"{temp_dir}/toc_anchor_book.epub"
            book = epub.EpubBook()
            book.set_identifier("toc-anchor-book")
            book.set_title("TOC Anchor Book")
            book.set_language("zh")

            chapter = epub.EpubHtml(
                title="Chapter",
                file_name="chapter.xhtml",
                content=(
                    "<html><body>"
                    "<div id='section'><h1>我们的现况</h1></div>"
                    "<h2 id='first'>1</h2><h2>世界生病了</h2>"
                    "<p>正文内容。</p>"
                    "</body></html>"
                ),
            )
            book.add_item(chapter)
            book.toc = (
                (
                    epub.Section("我们的现况", "chapter.xhtml#section"),
                    [epub.Link("chapter.xhtml#first", "1 世界生病了", "first")],
                ),
            )
            book.spine = [chapter]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            epub.write_epub(epub_path, book)

            config = get_azure_config()
            config.input_file = epub_path
            parser = get_book_parser(config)

            chapters = parser.get_chapters(" @BRK#")

        self.assertEqual([title for title, _ in chapters], ["我们的现况", "1 世界生病了"])
        self.assertEqual(chapters[0][1], "我们的现况")
        self.assertTrue(chapters[1][1].startswith("1 世界生病了"))
        self.assertIn("正文内容。", chapters[1][1])

    def test_insert_heading_pause_markers_preserves_heading_text(self):
        parser = object.__new__(EpubBookParser)
        soup = BeautifulSoup("<html><body><h1>序</h1><p>正文</p></body></html>", "lxml-xml")

        parser._insert_heading_pause_markers(soup)

        self.assertIn(f"序 {HEADING_PAUSE_MARKER.strip()} 正文", soup.get_text(strip=False))

    def test_insert_section_break_pause_markers_replaces_separator_text(self):
        parser = object.__new__(EpubBookParser)
        soup = BeautifulSoup("<html><body><p>上一节</p><p>***</p><p>下一节</p></body></html>", "lxml-xml")

        parser._insert_section_break_pause_markers(soup)

        self.assertIn(
            f"上一节 {SECTION_BREAK_PAUSE_MARKER.strip()} 下一节",
            soup.get_text(strip=False),
        )

    def test_unsupported_file_format(self):
        # Set up a config mock with an unsupported file extension
        config = MagicMock(input_file='book.unsupported')

        # Assert that NotImplementedError is raised for unsupported formats
        with self.assertRaises(NotImplementedError):
            get_book_parser(config)


if __name__ == '__main__':
    unittest.main()
