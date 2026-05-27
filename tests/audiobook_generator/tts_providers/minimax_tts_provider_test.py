import unittest

from audiobook_generator.tts_providers.minimax_tts_provider import (
    USD_PER_1000_CHAR,
    MinimaxTTSProvider,
    get_minimax_supported_models,
    get_minimax_supported_voice_display_names,
    get_minimax_supported_voices,
    resolve_minimax_voice_id,
)
from audiobook_generator.utils.heading_pause import (
    HEADING_PAUSE_MARKER,
    SECTION_BREAK_PAUSE_MARKER,
)


class TestMinimaxTTSProvider(unittest.TestCase):
    def test_estimate_cost_uses_fal_minimax_price(self):
        provider = object.__new__(MinimaxTTSProvider)
        provider.price = USD_PER_1000_CHAR

        self.assertEqual(provider.estimate_cost(1000000), 100)
        self.assertAlmostEqual(provider.estimate_cost(1), 0.10)

    def test_supported_models_keep_only_latest_28_series(self):
        self.assertEqual(
            get_minimax_supported_models(),
            [
                "fal-ai/minimax/speech-2.8-hd",
                "fal-ai/minimax/speech-2.8-turbo",
            ],
        )

    def test_voice_display_names_resolve_to_official_ids(self):
        self.assertEqual(
            get_minimax_supported_voice_display_names(),
            ["温暖闺蜜", "真诚青年"],
        )
        self.assertEqual(
            get_minimax_supported_voices(),
            [
                "Chinese (Mandarin)_Warm_Bestie",
                "Chinese (Mandarin)_Sincere_Adult",
            ],
        )
        self.assertEqual(
            resolve_minimax_voice_id("温暖闺蜜"),
            "Chinese (Mandarin)_Warm_Bestie",
        )

    def test_prepare_text_converts_heading_pause_to_native_marker(self):
        provider = object.__new__(MinimaxTTSProvider)
        provider._heading_pause_duration = 1.2
        provider._paragraph_pause_duration = 0.5
        provider._section_break_pause_duration = 1.8

        prepared = provider._prepare_text(
            f"序 {HEADING_PAUSE_MARKER.strip()} 正文 @BRK# 第二段"
        )

        self.assertEqual(prepared, "序 <#1.2#> 正文 <#0.5#> 第二段")

    def test_prepare_text_converts_regular_break_to_paragraph_pause(self):
        provider = object.__new__(MinimaxTTSProvider)
        provider._heading_pause_duration = 1.2
        provider._paragraph_pause_duration = 0.5
        provider._section_break_pause_duration = 1.8

        prepared = provider._prepare_text("第一段 @BRK# 第二段")

        self.assertEqual(prepared, "第一段 <#0.5#> 第二段")

    def test_prepare_text_converts_section_break_to_long_pause(self):
        provider = object.__new__(MinimaxTTSProvider)
        provider._heading_pause_duration = 1.2
        provider._paragraph_pause_duration = 0.5
        provider._section_break_pause_duration = 1.8

        prepared = provider._prepare_text(
            f"上一节 @BRK# {SECTION_BREAK_PAUSE_MARKER.strip()} @BRK# 下一节"
        )

        self.assertEqual(prepared, "上一节 <#1.8#> 下一节")

    def test_prepare_text_avoids_duplicate_paragraph_pause_after_heading(self):
        provider = object.__new__(MinimaxTTSProvider)
        provider._heading_pause_duration = 1.2
        provider._paragraph_pause_duration = 0.5
        provider._section_break_pause_duration = 1.8

        prepared = provider._prepare_text(
            f"序 {HEADING_PAUSE_MARKER.strip()} @BRK# 正文"
        )

        self.assertEqual(prepared, "序 <#1.2#> 正文")


if __name__ == "__main__":
    unittest.main()
