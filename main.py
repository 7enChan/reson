import argparse
from pathlib import Path

from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.core.audiobook_generator import AudiobookGenerator
from audiobook_generator.tts_providers.base_tts_provider import (
    get_supported_tts_providers,
)
from audiobook_generator.tts_providers.qwen_tts_provider import (
    get_qwen_supported_language_types,
    get_qwen_supported_models,
    get_qwen_supported_voices,
)
from audiobook_generator.tts_providers.minimax_tts_provider import (
    get_minimax_supported_voices,
    get_minimax_supported_language_boosts,
)
from audiobook_generator.utils.log_handler import setup_logging, generate_unique_log_path


def handle_args():
    parser = argparse.ArgumentParser(description="Convert text book to audiobook")
    parser.add_argument("input_file", help="Path to the EPUB file")
    parser.add_argument("output_folder", help="Path to the output folder")
    parser.add_argument(
        "--tts",
        choices=get_supported_tts_providers(),
        default=get_supported_tts_providers()[0],
           help="Choose TTS provider (default: azure). azure: Azure Cognitive Services, openai: OpenAI TTS API, edge: Microsoft Edge voices, gemini: Google Gemini 2.5 Pro Preview TTS, qwen3: Alibaba Qwen3 TTS, minimax: MiniMax Speech-02 HD, piper: Piper local/Docker voices. When using azure, environment variables MS_TTS_KEY and MS_TTS_REGION must be set. When using openai, environment variable OPENAI_API_KEY must be set. When using gemini, environment variable GOOGLE_API_KEY must be set unless --gemini_api_key is provided. When using qwen3, environment variable DASHSCOPE_API_KEY must be set unless --qwen_api_key is provided. When using minimax, environment variable FAL_KEY must be set unless --minimax_api_key is provided.",
    )
    parser.add_argument(
        "--log",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log level (default: INFO), can be DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Enable preview mode. In preview mode, the script will not convert the text to speech. Instead, it will print the chapter index, titles, and character counts.",
    )
    parser.add_argument(
        "--no_prompt",
        action="store_true",
        help="Don't ask the user if they wish to continue after estimating the cloud cost for TTS. Useful for scripting.",
    )
    parser.add_argument(
        "--language",
        default="en-US",
        help="Language for the text-to-speech service (default: en-US). For Azure TTS (--tts=azure), check https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts#text-to-speech for supported languages. For OpenAI TTS (--tts=openai), their API detects the language automatically. But setting this will also help on splitting the text into chunks with different strategies in this tool, especially for Chinese characters. For Chinese books, use zh-CN, zh-TW, or zh-HK.",
    )
    parser.add_argument(
        "--newline_mode",
        choices=["single", "double", "none"],
        default="double",
        help="Choose the mode of detecting new paragraphs: 'single', 'double', or 'none'. 'single' means a single newline character, while 'double' means two consecutive newline characters. 'none' means all newline characters will be replace with blank so paragraphs will not be detected. (default: double, works for most ebooks but will detect less paragraphs for some ebooks)",
    )
    parser.add_argument(
        "--title_mode",
        choices=["auto", "tag_text", "first_few"],
        default="auto",
        help="Choose the parse mode for chapter title, 'tag_text' search 'title','h1','h2','h3' tag for title, 'first_few' set first 60 characters as title, 'auto' auto apply the best mode for current chapter.",
    )
    parser.add_argument(
        "--chapter_start",
        default=1,
        type=int,
        help="Chapter start index (default: 1, starting from 1)",
    )
    parser.add_argument(
        "--chapter_end",
        default=-1,
        type=int,
        help="Chapter end index (default: -1, meaning to the last chapter)",
    )
    parser.add_argument(
        "--output_text",
        action="store_true",
        help="Enable Output Text. This will export a plain text file for each chapter specified and write the files to the output folder specified.",
    )
    parser.add_argument(
        "--remove_endnotes",
        action="store_true",
        help="This will remove endnote numbers from the end or middle of sentences. This is useful for academic books.",
    )

    parser.add_argument(
        "--remove_reference_numbers",
        action="store_true",
        help="This will remove reference numbers from the end or middle of sentences (e.g [3] or [12.1]). Also useful for academic books."
    )

    parser.add_argument(
        "--search_and_replace_file",
        default="",
        help="""Path to a file that contains 1 regex replace per line, to help with fixing pronunciations, etc. The format is:
        <search>==<replace>
        Note that you may have to specify word boundaries, to avoid replacing parts of words.
        """,
    )

    parser.add_argument(
        "--worker_count",
        type=int,
        default=1,
        help="Specifies the number of parallel workers to use for audiobook generation. "
        "Increasing this value can significantly speed up the process by processing multiple chapters simultaneously. "
        "Note: Chapters may not be processed in sequential order, but this will not affect the final audiobook.",
    )

    parser.add_argument(
        "--use_pydub_merge",
        action="store_true",
        help="Use pydub to merge audio segments of one chapter into single file instead of direct write. "
        "Currently only supported for OpenAI and Azure TTS. "
        "Direct write is faster but might skip audio segments if formats differ. "
        "Pydub merge is slower but more reliable for different audio formats. It requires ffmpeg to be installed first. "
        "You can use this option to avoid the issue of skipping audio segments in some cases. "
        "However, it's recommended to use direct write for most cases as it's faster. "
        "Only use this option if you encounter issues with direct write.",
    )

    parser.add_argument(
        "--voice_name",
        help="Various TTS providers has different voice names, look up for your provider settings.",
    )

    parser.add_argument(
        "--output_format",
        help="Output format for the text-to-speech service. Supported format depends on selected TTS provider",
    )

    parser.add_argument(
        "--model_name",
        help="Various TTS providers has different neural model names",
    )

    openai_tts_group = parser.add_argument_group(title="openai specific")
    openai_tts_group.add_argument(
        "--speed",
        default=1.0,
        type=float,
        help="The speed of the generated audio. Select a value from 0.25 to 4.0. 1.0 is the default.",
    )

    openai_tts_group.add_argument(
        "--instructions",
        help="Instructions for the TTS model. Only supported for 'gpt-4o-mini-tts' model.",
    )

    edge_tts_group = parser.add_argument_group(title="edge specific")
    edge_tts_group.add_argument(
        "--voice_rate",
        help="""
            Speaking rate of the text. Valid relative values range from -50%%(--xxx='-50%%') to +100%%. 
            For negative value use format --arg=value,
        """,
    )

    edge_tts_group.add_argument(
        "--voice_volume",
        help="""
            Volume level of the speaking voice. Valid relative values floor to -100%%.
            For negative value use format --arg=value,
        """,
    )

    edge_tts_group.add_argument(
        "--voice_pitch",
        help="""
            Baseline pitch for the text.Valid relative values like -80Hz,+50Hz, pitch changes should be within 0.5 to 1.5 times the original audio.
            For negative value use format --arg=value,
        """,
    )

    edge_tts_group.add_argument(
        "--proxy",
        help="Proxy server for the TTS provider. Format: http://[username:password@]proxy.server:port",
    )

    azure_edge_tts_group = parser.add_argument_group(title="azure/edge specific")
    azure_edge_tts_group.add_argument(
        "--break_duration",
        default="1250",
        help="Break duration in milliseconds for the different paragraphs or sections (default: 1250, means 1.25 s). Valid values range from 0 to 5000 milliseconds for Azure TTS.",
    )

    piper_tts_group = parser.add_argument_group(title="piper specific")
    piper_tts_group.add_argument(
        "--piper_path",
        default="piper",
        help="Path to the Piper TTS executable",
    )
    piper_tts_group.add_argument(
        "--piper_docker_image",
        default="lscr.io/linuxserver/piper:latest",
        help="Piper Docker image name (if using Docker)",
    )
    piper_tts_group.add_argument(
        "--piper_speaker",
        default=0,
        help="Piper speaker id, used for multi-speaker models",
    )
    piper_tts_group.add_argument(
        "--piper_sentence_silence",
        default=0.2,
        help="Seconds of silence after each sentence",
    )
    piper_tts_group.add_argument(
        "--piper_length_scale",
        default=1.0,
        help="Phoneme length, a.k.a. speaking rate",
    )

    gemini_tts_group = parser.add_argument_group(title="gemini specific")
    gemini_tts_group.add_argument(
        "--gemini_api_key",
        help="Google API key for Gemini TTS. Defaults to GOOGLE_API_KEY environment variable if not provided.",
    )
    gemini_tts_group.add_argument(
        "--gemini_audio_encoding",
        default="pcm16",
        help="Audio encoding of Gemini inline data payload (default: pcm16).",
    )
    gemini_tts_group.add_argument(
        "--gemini_sample_rate",
        type=int,
        default=24000,
        help="Sample rate in Hz for Gemini PCM output (default: 24000).",
    )
    gemini_tts_group.add_argument(
        "--gemini_channels",
        type=int,
        default=1,
        help="Number of channels in Gemini PCM output (default: 1).",
    )
    gemini_tts_group.add_argument(
        "--gemini_speaker_map",
        help="JSON object mapping speaker labels to Gemini voice names for multi-speaker prompts, e.g. '{\"Joe\": \"Kore\", \"Jane\": \"Puck\"}'.",
    )
    gemini_tts_group.add_argument(
        "--gemini_temperature",
        type=float,
        default=0.2,
        help="Sampling temperature for Gemini TTS (0.0-1.0). Lower values sound more consistent. Default: 0.2",
    )

    qwen_tts_group = parser.add_argument_group(title="qwen3 specific")
    qwen_tts_group.add_argument(
        "--qwen_api_key",
        help="DashScope API key for Qwen3 TTS. Defaults to DASHSCOPE_API_KEY environment variable if not provided.",
    )
    qwen_tts_group.add_argument(
        "--qwen_language_type",
        choices=get_qwen_supported_language_types(),
        help="Language type parameter accepted by Qwen3 TTS (e.g. Chinese, English).",
    )
    qwen_tts_group.add_argument(
        "--qwen_stream",
        action="store_true",
        help="Enable streaming responses. Audio chunks will be reassembled locally before writing to disk.",
    )
    qwen_tts_group.add_argument(
        "--qwen_request_timeout",
        type=int,
        help="Timeout in seconds for downloading Qwen audio URLs (default: 30).",
    )
    qwen_tts_group.add_argument(
        "--qwen_model",
        dest="model_name",
        choices=get_qwen_supported_models(),
        help="Model name for Qwen3 TTS (alias of --model_name).",
    )
    qwen_tts_group.add_argument(
        "--qwen_voice",
        dest="voice_name",
        choices=get_qwen_supported_voices(),
        help="Voice name for Qwen3 TTS (alias of --voice_name).",
    )

    minimax_tts_group = parser.add_argument_group(title="minimax specific")
    minimax_tts_group.add_argument(
        "--minimax_api_key",
        help="FAL API key for MiniMax TTS. Defaults to FAL_KEY environment variable if not provided.",
    )
    minimax_tts_group.add_argument(
        "--minimax_speed",
        type=float,
        default=1.0,
        help="Speech speed for MiniMax TTS (0.5-2.0, default: 1.0).",
    )
    minimax_tts_group.add_argument(
        "--minimax_volume",
        type=float,
        default=1.0,
        help="Speech volume for MiniMax TTS (0.1-2.0, default: 1.0).",
    )
    minimax_tts_group.add_argument(
        "--minimax_pitch",
        type=float,
        default=0.0,
        help="Speech pitch for MiniMax TTS (-12 to 12, default: 0).",
    )
    minimax_tts_group.add_argument(
        "--minimax_language_boost",
        choices=get_minimax_supported_language_boosts(),
        help="Language boost for MiniMax TTS to enhance recognition of specified languages.",
    )
    minimax_tts_group.add_argument(
        "--minimax_request_timeout",
        type=int,
        help="Timeout in seconds for downloading MiniMax audio URLs (default: 60).",
    )
    minimax_tts_group.add_argument(
        "--minimax_voice",
        dest="voice_name",
        choices=get_minimax_supported_voices(),
        help="Voice name for MiniMax TTS (alias of --voice_name).",
    )

    args = parser.parse_args()
    return GeneralConfig(args)


def main(config=None, log_file=None):
    if not config: # config passed from UI, or uses args if CLI
        config = handle_args()

    if log_file:
        # If log_file is provided (e.g., from UI), use it directly as a Path object.
        # The UI passes an absolute path string.
        effective_log_file = Path(log_file)
    else:
        # Otherwise (e.g., CLI usage without a specific log file from UI),
        # generate a unique log file name.
        effective_log_file = generate_unique_log_path("EtA")
    
    # Ensure config.log_file is updated, as it's used by AudiobookGenerator for worker processes.
    config.log_file = effective_log_file

    setup_logging(config.log, str(effective_log_file))

    AudiobookGenerator(config).run()


if __name__ == "__main__":
    main()
