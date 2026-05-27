import unittest
from unittest.mock import MagicMock

from audiobook_generator.utils.heading_pause import (
    DEFAULT_MINIMAX_HEADING_PAUSE_SECONDS,
    format_minimax_pause_marker,
    get_minimax_narration_preset_values,
    resolve_minimax_narration_rhythm,
    resolve_minimax_heading_pause_duration,
    should_insert_minimax_heading_pause,
    should_insert_minimax_section_break_pause,
)


class TestHeadingPause(unittest.TestCase):
    def test_resolve_uses_default_for_missing_or_invalid_values(self):
        self.assertEqual(
            resolve_minimax_heading_pause_duration(None),
            DEFAULT_MINIMAX_HEADING_PAUSE_SECONDS,
        )
        self.assertEqual(
            resolve_minimax_heading_pause_duration("invalid"),
            DEFAULT_MINIMAX_HEADING_PAUSE_SECONDS,
        )

    def test_format_minimax_pause_marker_trims_unneeded_decimals(self):
        self.assertEqual(format_minimax_pause_marker(1.2), "<#1.2#>")
        self.assertEqual(format_minimax_pause_marker(2), "<#2#>")

    def test_zero_pause_duration_disables_native_pause(self):
        self.assertEqual(resolve_minimax_heading_pause_duration(0), 0.0)
        self.assertEqual(format_minimax_pause_marker(0), "\n\n")

    def test_meditative_preset_values_are_slower_than_concise(self):
        meditative = get_minimax_narration_preset_values("Meditative")
        concise = get_minimax_narration_preset_values("Concise")

        self.assertGreater(meditative["paragraph"], concise["paragraph"])
        self.assertGreater(meditative["section_break"], concise["section_break"])

    def test_resolve_narration_rhythm_allows_explicit_overrides(self):
        rhythm = resolve_minimax_narration_rhythm(
            MagicMock(
                minimax_narration_preset="Meditative",
                minimax_heading_pause_duration=None,
                minimax_paragraph_pause_duration=0.4,
                minimax_section_break_pause_duration=None,
                minimax_chapter_ending_silence_duration=0,
            )
        )

        self.assertEqual(rhythm.heading_pause, 1.2)
        self.assertEqual(rhythm.paragraph_pause, 0.4)
        self.assertEqual(rhythm.section_break_pause, 2.0)
        self.assertEqual(rhythm.chapter_ending_silence, 0.0)

    def test_should_insert_only_for_enabled_minimax_config(self):
        self.assertTrue(
            should_insert_minimax_heading_pause(
                MagicMock(
                    tts="minimax",
                    minimax_narration_preset=None,
                    minimax_heading_pause_duration=1.2,
                    minimax_paragraph_pause_duration=None,
                    minimax_section_break_pause_duration=None,
                    minimax_chapter_ending_silence_duration=None,
                )
            )
        )
        self.assertFalse(
            should_insert_minimax_heading_pause(
                MagicMock(tts="edge", minimax_heading_pause_duration=1.2)
            )
        )
        self.assertFalse(
            should_insert_minimax_heading_pause(
                MagicMock(
                    tts="minimax",
                    minimax_narration_preset=None,
                    minimax_heading_pause_duration=0,
                    minimax_paragraph_pause_duration=None,
                    minimax_section_break_pause_duration=None,
                    minimax_chapter_ending_silence_duration=None,
                )
            )
        )

    def test_section_break_insert_uses_section_duration(self):
        self.assertTrue(
            should_insert_minimax_section_break_pause(
                MagicMock(
                    tts="minimax",
                    minimax_narration_preset="Natural",
                    minimax_heading_pause_duration=None,
                    minimax_paragraph_pause_duration=None,
                    minimax_section_break_pause_duration=1.8,
                    minimax_chapter_ending_silence_duration=None,
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
