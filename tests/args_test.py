import unittest
from unittest.mock import patch

from audiobook_generator.tts_providers.base_tts_provider import (
    get_supported_tts_providers,
)
from main import handle_args


class TestHandleArgs(unittest.TestCase):

    # Test azure arguments
    @patch('sys.argv', ['program', 'input_file.epub', 'output_folder', '--tts', 'azure'])
    def test_azure_args(self):
        config = handle_args()
        self.assertEqual(config.tts, 'azure')

    # Test openai arguments
    @patch('sys.argv', ['program', 'input_file.epub', 'output_folder', '--tts', 'openai'])
    def test_openai_args(self):
        config = handle_args()
        self.assertEqual(config.tts, 'openai')

    # Test gemini arguments
    @patch('sys.argv', ['program', 'input_file.epub', 'output_folder', '--tts', 'gemini',
                        '--gemini_sample_rate', '24000', '--gemini_channels', '1', '--gemini_temperature', '0.1',
                        '--output_format', 'wav'])
    def test_gemini_args(self):
        config = handle_args()
        self.assertEqual(config.tts, 'gemini')
        self.assertEqual(config.gemini_sample_rate, 24000)
        self.assertEqual(config.gemini_channels, 1)
        self.assertAlmostEqual(config.gemini_temperature, 0.1)
        self.assertEqual(config.output_format, 'wav')

    @patch('sys.argv', ['program', 'input_file.epub', 'output_folder', '--tts', 'qwen3',
                        '--qwen_language_type', 'English', '--qwen_request_timeout', '45', '--qwen_stream'])
    def test_qwen3_args(self):
        config = handle_args()
        self.assertEqual(config.tts, 'qwen3')
        self.assertEqual(config.qwen_language_type, 'English')
        self.assertTrue(config.qwen_stream)
        self.assertEqual(config.qwen_request_timeout, 45)

    # Test unsupported TTS provider
    @patch('sys.argv', ['program', 'input_file.epub', 'output_folder', '--tts', 'unsupported_tts'])
    def test_unsupported_tts(self):
        with self.assertRaises(SystemExit):  # argparse exits with SystemExit on error
            handle_args()

    # Test missing required input_file argument
    @patch('sys.argv', ['program', 'output_folder', '--tts', 'azure'])
    def test_missing_input_file(self):
        with self.assertRaises(SystemExit):
            handle_args()

    # Test invalid log level argument
    @patch('sys.argv', ['program', 'input_file.epub', 'output_folder', '--log', 'INVALID_LOG_LEVEL'])
    def test_invalid_log_level(self):
        with self.assertRaises(SystemExit):
            handle_args()

    def test_gemini_provider_in_supported_list(self):
        providers = get_supported_tts_providers()
        self.assertIn('gemini', providers)

    def test_qwen3_provider_in_supported_list(self):
        providers = get_supported_tts_providers()
        self.assertIn('qwen3', providers)


if __name__ == '__main__':
    unittest.main()
