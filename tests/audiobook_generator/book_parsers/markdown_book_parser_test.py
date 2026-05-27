import unittest

from audiobook_generator.book_parsers.base_book_parser import get_book_parser
from audiobook_generator.book_parsers.markdown_book_parser import MarkdownBookParser
from audiobook_generator.utils.heading_pause import (
    HEADING_PAUSE_MARKER,
    SECTION_BREAK_PAUSE_MARKER,
)
from tests.test_utils import get_markdown_config


class TestMarkdownBookParser(unittest.TestCase):
    def setUp(self):
        self.config = get_markdown_config()
        self.parser = get_book_parser(self.config)

    def test_get_markdown_book_parser(self):
        self.assertIsInstance(self.parser, MarkdownBookParser)
        self.assertEqual(self.parser.get_book_title(), "Sample Markdown Adventure")
        self.assertEqual(self.parser.get_book_author(), "Jane Doe")

    def test_get_chapters(self):
        chapters = self.parser.get_chapters(" @BRK#")
        self.assertEqual(len(chapters), 3)

        titles = [title for title, _ in chapters]
        self.assertEqual(titles[0], "Prologue")
        self.assertEqual(titles[1], "Chapter One")
        self.assertEqual(titles[2], "Chapter Two")

        first_chapter_text = chapters[0][1]
        self.assertTrue(first_chapter_text.startswith("Prologue"))
        self.assertIn("@BRK#", first_chapter_text)
        self.assertNotIn("**", first_chapter_text)
        self.assertNotIn("[link]", first_chapter_text)

    def test_minimax_heading_pause_marker_is_inserted_after_heading(self):
        config = get_markdown_config()
        config.tts = "minimax"
        config.minimax_heading_pause_duration = 1.2
        parser = MarkdownBookParser(config)

        chapters = parser.get_chapters(" @BRK#")

        self.assertTrue(
            chapters[0][1].startswith(
                f"Prologue {HEADING_PAUSE_MARKER.strip()} @BRK#"
            )
        )

    def test_section_break_marker_replaces_separator_lines(self):
        config = get_markdown_config()
        parser = MarkdownBookParser(config)

        lines = parser._insert_section_break_pause_markers(
            ["上一节", "***", "下一节"]
        )

        self.assertEqual(
            lines,
            ["上一节", SECTION_BREAK_PAUSE_MARKER.strip(), "下一节"],
        )


if __name__ == '__main__':
    unittest.main()
