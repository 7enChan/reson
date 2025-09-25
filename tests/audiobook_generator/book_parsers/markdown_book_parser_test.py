import unittest

from audiobook_generator.book_parsers.base_book_parser import get_book_parser
from audiobook_generator.book_parsers.markdown_book_parser import MarkdownBookParser
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
        self.assertEqual(titles[1], "Chapter_One")
        self.assertEqual(titles[2], "Chapter_Two")

        first_chapter_text = chapters[0][1]
        self.assertTrue(first_chapter_text.startswith("Prologue"))
        self.assertIn("@BRK#", first_chapter_text)
        self.assertNotIn("**", first_chapter_text)
        self.assertNotIn("[link]", first_chapter_text)


if __name__ == '__main__':
    unittest.main()
