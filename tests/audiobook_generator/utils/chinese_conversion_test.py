import unittest

from audiobook_generator.utils.chinese_conversion import (
    CHINESE_CONVERSION_NONE,
    convert_chapters,
    get_chinese_conversion_choices,
    normalize_chinese_conversion,
)


class TestChineseConversion(unittest.TestCase):
    def test_normalize_accepts_internal_values_and_labels(self):
        self.assertEqual(normalize_chinese_conversion("tw2s"), "tw2s")
        self.assertEqual(
            normalize_chinese_conversion("Taiwan Traditional to Simplified"),
            "tw2s",
        )
        self.assertEqual(normalize_chinese_conversion(None), CHINESE_CONVERSION_NONE)

    def test_choices_are_labels_for_webui(self):
        self.assertIn("None", get_chinese_conversion_choices())
        self.assertIn("Taiwan Traditional to Simplified", get_chinese_conversion_choices())

    def test_none_returns_original_chapters(self):
        chapters = [("標題", "臺灣繁體內容")]

        self.assertIs(convert_chapters(chapters, "none"), chapters)

    def test_tw2s_converts_title_and_text(self):
        chapters = [("標題", "臺灣繁體內容")]

        converted = convert_chapters(chapters, "tw2s")

        self.assertEqual(converted, [("标题", "台湾繁体内容")])

    def test_unknown_conversion_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Unsupported Chinese conversion"):
            normalize_chinese_conversion("bad-mode")


if __name__ == "__main__":
    unittest.main()
