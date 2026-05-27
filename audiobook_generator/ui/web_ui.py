from multiprocessing import Process
from typing import Optional
import os
from datetime import datetime

import gradio as gr
from gradio_log import Log
from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.tts_providers.azure_tts_provider import get_azure_supported_languages, \
    get_azure_supported_voices, get_azure_supported_output_formats
from audiobook_generator.tts_providers.edge_tts_provider import get_edge_tts_supported_voices, \
    get_edge_tts_supported_language, get_edge_tts_supported_output_formats
from audiobook_generator.tts_providers.openai_tts_provider import get_openai_supported_models, \
    get_openai_supported_voices, get_openai_instructions_example, get_openai_supported_output_formats
from audiobook_generator.tts_providers.gemini_tts_provider import get_gemini_supported_models, \
    get_gemini_supported_output_formats, get_gemini_supported_voices
from audiobook_generator.tts_providers.qwen_tts_provider import get_qwen_supported_language_types, \
    get_qwen_supported_models, get_qwen_supported_voices
from audiobook_generator.tts_providers.minimax_tts_provider import get_minimax_supported_voices, \
    get_minimax_supported_language_boosts, get_minimax_supported_models
from audiobook_generator.tts_providers.piper_tts_provider import get_piper_supported_languages, \
    get_piper_supported_voices, get_piper_supported_qualities, get_piper_supported_speakers
from audiobook_generator.utils.chinese_conversion import get_chinese_conversion_choices
from audiobook_generator.utils.heading_pause import (
    get_minimax_narration_preset_values,
    get_narration_rhythm_preset_choices,
)
from audiobook_generator.utils.log_handler import generate_unique_log_path
from main import main

DEFAULT_AZURE_VOICE = "zh-CN-XiaoxiaoMultilingualNeural"

selected_tts = "MiniMax"
running_process: Optional[Process] = None
webui_log_file = None

def on_tab_change(evt: gr.SelectData):
    print(f"{evt.value} tab selected")
    global selected_tts
    selected_tts = evt.value

def get_azure_voices_by_language(language):
    voices_list = [voice for voice in get_azure_supported_voices() if voice.startswith(language)]
    default_voice = DEFAULT_AZURE_VOICE if DEFAULT_AZURE_VOICE in voices_list else (voices_list[0] if voices_list else None)
    return gr.Dropdown(
        voices_list,
        value=default_voice,
        label="Voice",
        interactive=True,
        info="Select the voice"
    )

def get_edge_voices_by_language(language):
    voices_list = [voice for voice in get_edge_tts_supported_voices() if voice.startswith(language)]
    return gr.Dropdown(voices_list, value=voices_list[0], label="Voice", interactive=True, info="Select the voice")

def get_piper_supported_voices_gui(language):
    voices_list = get_piper_supported_voices(language)
    return gr.Dropdown(voices_list, value=voices_list[0], label="Voice", interactive=True, info="Select the voice")

def get_piper_supported_qualities_gui(language, voice):
    qualities_list = get_piper_supported_qualities(language, voice)
    return gr.Dropdown(qualities_list, value=qualities_list[0], label="Quality", interactive=True, info="Select the quality")

def get_piper_supported_speakers_gui(language, voice, quality):
    speakers_list = get_piper_supported_speakers(language, voice, quality)
    return gr.Dropdown(speakers_list, value=speakers_list[0], label="Speaker", interactive=True, info="Select the speaker")


def get_minimax_rhythm_controls(preset):
    values = get_minimax_narration_preset_values(preset)
    return (
        gr.Slider(value=values["heading"]),
        gr.Slider(value=values["paragraph"]),
        gr.Slider(value=values["section_break"]),
        gr.Slider(value=values["chapter_ending"]),
    )


def process_ui_form(input_file, output_dir, worker_count, log_level, output_text, preview, export_m4b,
                    search_and_replace_file, title_mode, new_line_mode, chinese_conversion, chapter_start, chapter_end, remove_endnotes, remove_reference_numbers,
                    azure_api_key, azure_region,
                    model, voices, speed, openai_output_format, instructions,
                    azure_language, azure_voice, azure_output_format, azure_break_duration,
                    edge_language, edge_voice, edge_output_format, proxy, edge_voice_rate, edge_volume, edge_pitch, edge_break_duration,
                    gemini_api_key, gemini_model, gemini_voice, gemini_output_format, gemini_sample_rate, gemini_channels, gemini_temperature, gemini_speaker_map, gemini_instructions,
                    qwen_api_key, qwen_model, qwen_voice, qwen_language_type, qwen_locale, qwen_stream, qwen_request_timeout,
                    minimax_api_key, minimax_model, minimax_voice, minimax_output_format, minimax_speed, minimax_volume, minimax_pitch, minimax_language_boost, minimax_request_timeout, minimax_narration_preset, minimax_heading_pause_duration, minimax_paragraph_pause_duration, minimax_section_break_pause_duration, minimax_chapter_ending_silence_duration,
                    piper_executable_path, piper_docker_image, piper_language, piper_voice, piper_quality, piper_speaker,
                    piper_noise_scale, piper_noise_w_scale, piper_length_scale, piper_sentence_silence):

    sanitized_key = (azure_api_key or "").strip()
    sanitized_region = (azure_region or "").strip()
    if sanitized_key:
        os.environ["MS_TTS_KEY"] = sanitized_key
    if sanitized_region:
        os.environ["MS_TTS_REGION"] = sanitized_region

    sanitized_gemini_key = (gemini_api_key or "").strip()
    if sanitized_gemini_key:
        os.environ["GOOGLE_API_KEY"] = sanitized_gemini_key

    sanitized_qwen_key = (qwen_api_key or "").strip()
    if sanitized_qwen_key:
        os.environ["DASHSCOPE_API_KEY"] = sanitized_qwen_key

    sanitized_minimax_key = (minimax_api_key or "").strip()
    if sanitized_minimax_key:
        os.environ["FAL_KEY"] = sanitized_minimax_key

    config = GeneralConfig(None)
    config.input_file = input_file.name if hasattr(input_file, 'name') else input_file
    config.output_folder = output_dir
    config.preview = preview
    config.output_text = output_text
    config.export_m4b = export_m4b
    config.log = log_level
    config.worker_count = worker_count
    config.no_prompt = True

    config.title_mode = title_mode
    config.newline_mode = new_line_mode
    config.chinese_conversion = chinese_conversion
    config.chapter_start = chapter_start
    config.chapter_end = chapter_end
    config.remove_endnotes = remove_endnotes
    config.remove_reference_numbers = remove_reference_numbers
    config.search_and_replace_file = search_and_replace_file.name if hasattr(search_and_replace_file, 'name') else search_and_replace_file

    global selected_tts
    if selected_tts == "OpenAI":
        config.tts = "openai"
        config.output_format = openai_output_format
        config.voice_name = voices
        config.model_name = model
        config.instructions = instructions
        config.speed = speed
    elif selected_tts == "Azure":
        config.tts = "azure"
        config.language = azure_language
        config.voice_name = azure_voice
        config.output_format = azure_output_format
        config.break_duration = azure_break_duration
    elif selected_tts == "Edge":
        config.tts = "edge"
        config.language = edge_language
        config.voice_name = edge_voice
        config.output_format = edge_output_format
        config.proxy = proxy
        config.voice_rate = f"{edge_voice_rate:+}%"
        config.voice_volume = f"{edge_volume:+}%"
        config.voice_pitch = f"{edge_pitch:+}Hz"
        config.break_duration = edge_break_duration
    elif selected_tts == "Gemini":
        config.tts = "gemini"
        config.model_name = gemini_model
        config.voice_name = gemini_voice
        config.output_format = gemini_output_format
        config.gemini_api_key = sanitized_gemini_key or None
        config.gemini_sample_rate = int(gemini_sample_rate) if gemini_sample_rate else None
        config.gemini_channels = int(gemini_channels) if gemini_channels else None
        config.gemini_temperature = float(gemini_temperature) if gemini_temperature is not None else None
        config.gemini_speaker_map = gemini_speaker_map.strip() if gemini_speaker_map else None
        config.instructions = gemini_instructions.strip() if gemini_instructions else None
    elif selected_tts == "Qwen3":
        config.tts = "qwen3"
        config.model_name = qwen_model or None
        config.voice_name = qwen_voice or None
        config.language = qwen_locale or None
        config.qwen_api_key = sanitized_qwen_key or None
        config.qwen_language_type = qwen_language_type or None
        config.qwen_stream = bool(qwen_stream)
        config.qwen_request_timeout = int(qwen_request_timeout) if qwen_request_timeout else None
        config.output_format = "wav"
    elif selected_tts == "MiniMax":
        config.tts = "minimax"
        config.model_name = minimax_model or None
        config.voice_name = minimax_voice or None
        config.output_format = minimax_output_format or "mp3"
        config.minimax_api_key = sanitized_minimax_key or None
        config.minimax_speed = float(minimax_speed) if minimax_speed is not None else None
        config.minimax_volume = float(minimax_volume) if minimax_volume is not None else None
        config.minimax_pitch = float(minimax_pitch) if minimax_pitch is not None else None
        config.minimax_language_boost = minimax_language_boost or None
        config.minimax_request_timeout = int(minimax_request_timeout) if minimax_request_timeout else None
        config.minimax_narration_preset = minimax_narration_preset or None
        config.minimax_heading_pause_duration = float(minimax_heading_pause_duration) if minimax_heading_pause_duration is not None else None
        config.minimax_paragraph_pause_duration = float(minimax_paragraph_pause_duration) if minimax_paragraph_pause_duration is not None else None
        config.minimax_section_break_pause_duration = float(minimax_section_break_pause_duration) if minimax_section_break_pause_duration is not None else None
        config.minimax_chapter_ending_silence_duration = float(minimax_chapter_ending_silence_duration) if minimax_chapter_ending_silence_duration is not None else None
    elif selected_tts == "Piper":
        config.tts = "piper"
        config.piper_path = piper_executable_path
        config.piper_docker_image = piper_docker_image
        config.model_name = f"{piper_language}-{piper_voice}-{piper_quality}"
        config.piper_speaker = piper_speaker
        config.piper_noise_scale = piper_noise_scale
        config.piper_noise_w_scale = piper_noise_w_scale
        config.piper_length_scale = piper_length_scale
        config.piper_sentence_silence = piper_sentence_silence
    else:
        raise ValueError("Unsupported TTS provider selected")

    launch_audiobook_generator(config)


def launch_audiobook_generator(config):
    global running_process
    if running_process and running_process.is_alive():
        print("Audiobook generator already running")
        return

    running_process = Process(target=main, args=(config, str(webui_log_file.absolute())))
    running_process.start()


def terminate_audiobook_generator():
    global running_process
    if running_process and running_process.is_alive():
        running_process.terminate()
        running_process = None
        print("Audiobook generator terminated manually")

def host_ui(config):
    default_output_dir = os.path.join("audiobook_output", datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    print(f"Default audiobook output directory: {default_output_dir}")
    custom_css = """
    :root {
        --reson-bg: #fdfbf7;
        --reson-surface: #ffffff;
        --reson-muted: #f3eee6;
        --reson-border: #e7dfd2;
        --reson-text: #1f2933;
        --reson-subtle: #647067;
        --reson-primary: #8a4b16;
        --reson-primary-hover: #733f12;
        --reson-on-primary: #ffffff;
        --reson-primary-soft: #f6ead9;
        --reson-accent: #b45309;
        --reson-step-title: #8a4b16;
        --reson-input: #ffffff;
        --reson-code-bg: #111827;
    }
    @media (prefers-color-scheme: dark) {
        :root {
            --reson-bg: #12100d;
            --reson-surface: #1b1712;
            --reson-muted: #241f18;
            --reson-border: #3b3328;
            --reson-text: #f7efe3;
            --reson-subtle: #b8aa96;
            --reson-primary: #e8c48b;
            --reson-primary-hover: #f0d3a2;
            --reson-on-primary: #0b0a08;
            --reson-primary-soft: #3b2b18;
            --reson-accent: #f59e0b;
            --reson-step-title: #e8c48b;
            --reson-input: #211c16;
            --reson-code-bg: #0b0a08;
        }
    }
    html.dark, body.dark, .dark, [data-theme="dark"], gradio-app.dark {
        --reson-bg: #12100d;
        --reson-surface: #1b1712;
        --reson-muted: #241f18;
        --reson-border: #3b3328;
        --reson-text: #f7efe3;
        --reson-subtle: #b8aa96;
        --reson-primary: #e8c48b;
        --reson-primary-hover: #f0d3a2;
        --reson-on-primary: #0b0a08;
        --reson-primary-soft: #3b2b18;
        --reson-accent: #f59e0b;
        --reson-step-title: #e8c48b;
        --reson-input: #211c16;
        --reson-code-bg: #0b0a08;
    }
    body, .gradio-container, gradio-app {
        --body-background-fill: var(--reson-bg) !important;
        --body-text-color: var(--reson-text) !important;
        --block-background-fill: var(--reson-surface) !important;
        --block-border-color: var(--reson-border) !important;
        --block-label-background-fill: var(--reson-muted) !important;
        --block-label-border-color: var(--reson-border) !important;
        --block-label-text-color: var(--reson-text) !important;
        --input-background-fill: var(--reson-input) !important;
        --input-border-color: var(--reson-border) !important;
        --input-placeholder-color: var(--reson-subtle) !important;
        --button-primary-background-fill: var(--reson-primary) !important;
        --button-primary-background-fill-hover: var(--reson-primary-hover) !important;
        --button-primary-border-color: var(--reson-primary) !important;
        --button-primary-text-color: var(--reson-on-primary) !important;
        --button-secondary-background-fill: var(--reson-surface) !important;
        --button-secondary-background-fill-hover: var(--reson-muted) !important;
        --button-secondary-border-color: var(--reson-border) !important;
        --button-secondary-text-color: var(--reson-text) !important;
        --border-color-primary: var(--reson-border) !important;
        --border-color-accent: var(--reson-primary) !important;
        background: var(--reson-bg) !important;
        color: var(--reson-text) !important;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    }
    .gradio-container {
        max-width: 1180px !important;
        margin: 0 auto !important;
        padding: 28px 20px 48px !important;
    }
    .app-hero {
        border: 1px solid var(--reson-border);
        background: var(--reson-surface);
        color: var(--reson-text);
        border-radius: 14px;
        padding: 28px 30px;
        margin-bottom: 18px;
    }
    .app-hero h1 {
        margin: 0 0 8px;
        font-size: 30px;
        line-height: 1.2;
        letter-spacing: 0;
    }
    .app-hero p {
        margin: 0;
        color: var(--reson-subtle);
        font-size: 15px;
        line-height: 1.6;
    }
    .action-row {
        margin-top: 22px;
    }
    .section-panel {
        border: 1px solid var(--reson-border);
        background: var(--reson-surface);
        color: var(--reson-text);
        border-radius: 12px;
        padding: 18px;
        margin: 14px 0;
    }
    .section-panel h2, .section-panel h3 {
        margin-top: 0;
    }
    button.primary, .gradio-button.primary {
        background: var(--reson-primary) !important;
        border-color: var(--reson-primary) !important;
        color: var(--reson-on-primary) !important;
    }
    button.primary:hover, .gradio-button.primary:hover {
        background: var(--reson-primary-hover) !important;
        border-color: var(--reson-primary-hover) !important;
    }
    .gradio-container label {
        color: var(--reson-text) !important;
        font-weight: 600 !important;
    }
    .gradio-container input,
    .gradio-container textarea,
    .gradio-container select {
        background: var(--reson-input) !important;
        color: var(--reson-text) !important;
        border-color: var(--reson-border) !important;
    }
    .gradio-container input::placeholder,
    .gradio-container textarea::placeholder {
        color: var(--reson-subtle) !important;
    }
    .gradio-container .block,
    .gradio-container .form,
    .gradio-container .tabs,
    .gradio-container .tabitem,
    .gradio-container .panel,
    .gradio-container .wrap {
        border-color: var(--reson-border) !important;
    }
    .gradio-container .prose,
    .gradio-container .markdown,
    .gradio-container h1,
    .gradio-container h2,
    .gradio-container h3,
    .gradio-container p,
    .gradio-container span {
        color: inherit;
    }
    .gradio-container .secondary {
        border-color: var(--reson-border) !important;
    }
    .gradio-container .tabs {
        width: 100% !important;
    }
    .gradio-container .tabitem {
        width: 100% !important;
        padding: 22px 0 0 !important;
    }
    details, .gr-accordion {
        border-color: var(--reson-border) !important;
        background: var(--reson-surface) !important;
        color: var(--reson-text) !important;
    }
    pre, code {
        background: var(--reson-code-bg) !important;
        color: var(--reson-text) !important;
    }
    .footer-hint {
        color: var(--reson-subtle);
        font-size: 13px;
        line-height: 1.5;
    }
    @media (max-width: 1080px) {
        .gradio-container {
            padding-left: 12px !important;
            padding-right: 12px !important;
        }
        .app-hero {
            padding: 22px 18px;
        }
    }
    """

    with gr.Blocks(analytics_enabled=False, title="Epub to Audiobook Converter", css=custom_css) as ui:
        gr.Markdown(
            """
            <div class="app-hero">
              <h1>Reson</h1>
              <p>Before words, there was voice.</p>
            </div>
            """
        )
        with gr.Row(equal_height=False, elem_classes="main-workspace"):
            with gr.Column(scale=5, min_width=560, elem_classes="engine-pane"):
                gr.Markdown("## 声音处理引擎")
                with gr.Tabs(selected="minimax_tab_id"):
                    with gr.Tab("MiniMax", id="minimax_tab_id") as minimax_tab:
                        minimax_tab.select(on_tab_change, inputs=None, outputs=None)

                        with gr.Row(equal_height=True):
                            minimax_api_key = gr.Textbox(
                                label="MiniMax / FAL API Key",
                                value=os.environ.get("FAL_KEY", ""),
                                placeholder="Automatically saved to browser storage",
                                type="password",
                                interactive=True,
                                elem_id="minimax_api_key",
                                scale=1,
                            )
                            minimax_model = gr.Dropdown(
                                get_minimax_supported_models(),
                                label="模型",
                                value="fal-ai/minimax/speech-2.8-hd",
                                interactive=True,
                                scale=2,
                            )
                            minimax_language_boost = gr.Dropdown(
                                get_minimax_supported_language_boosts(),
                                label="语言增强",
                                value=None,
                                interactive=True,
                                scale=1,
                            )
                        minimax_rhythm_defaults = get_minimax_narration_preset_values("Natural")

                        with gr.Row(equal_height=True):
                            minimax_voice = gr.Dropdown(
                                get_minimax_supported_voices(),
                                label="朗读声音",
                                value="Chinese (Mandarin)_Warm_Bestie",
                                interactive=True,
                                allow_custom_value=True,
                            )
                            minimax_speed = gr.Slider(
                                minimum=0.5,
                                maximum=2.0,
                                step=0.1,
                                label="语速",
                                value=1.0,
                            )
                            minimax_pitch = gr.Slider(
                                minimum=-12,
                                maximum=12,
                                step=1,
                                label="音高",
                                value=0,
                            )

                        with gr.Accordion("MiniMax 专业参数", open=False):
                            with gr.Row(equal_height=True):
                                minimax_narration_preset = gr.Dropdown(
                                    get_narration_rhythm_preset_choices(),
                                    label="朗读节奏",
                                    value="Natural",
                                    interactive=True,
                                )
                                minimax_volume = gr.Slider(
                                    minimum=0.1,
                                    maximum=2.0,
                                    step=0.1,
                                    label="音量",
                                    value=1.0,
                                    info="默认 1.0。",
                                )
                                minimax_request_timeout = gr.Slider(
                                    minimum=10,
                                    maximum=180,
                                    step=5,
                                    label="下载超时（秒）",
                                    value=60,
                                    info="网络慢或长章节失败时再调高。",
                                )

                            with gr.Row(equal_height=True):
                                minimax_heading_pause_duration = gr.Slider(
                                    minimum=0,
                                    maximum=5,
                                    step=0.1,
                                    label="标题后停顿（秒）",
                                    value=minimax_rhythm_defaults["heading"],
                                    info="章节标题和正文之间的停顿。",
                                )
                                minimax_paragraph_pause_duration = gr.Slider(
                                    minimum=0,
                                    maximum=2,
                                    step=0.05,
                                    label="段落停顿（秒）",
                                    value=minimax_rhythm_defaults["paragraph"],
                                    info="段落之间的自然停顿。",
                                )

                            with gr.Row(equal_height=True):
                                minimax_section_break_pause_duration = gr.Slider(
                                    minimum=0,
                                    maximum=5,
                                    step=0.1,
                                    label="小节停顿（秒）",
                                    value=minimax_rhythm_defaults["section_break"],
                                    info="分隔符或场景切换处的停顿。",
                                )
                                minimax_chapter_ending_silence_duration = gr.Slider(
                                    minimum=0,
                                    maximum=5,
                                    step=0.1,
                                    label="章节结尾留白（秒）",
                                    value=minimax_rhythm_defaults["chapter_ending"],
                                    info="每章音频末尾额外留白。",
                                )
                            minimax_narration_preset.change(
                                fn=get_minimax_rhythm_controls,
                                inputs=minimax_narration_preset,
                                outputs=[
                                    minimax_heading_pause_duration,
                                    minimax_paragraph_pause_duration,
                                    minimax_section_break_pause_duration,
                                    minimax_chapter_ending_silence_duration,
                                ],
                            )

                    with gr.Tab("OpenAI", id="openai_tab_id") as open_ai_tab:
                        gr.Markdown("It is expected that user configured: `OPENAI_API_KEY` in the environment variables. Optionally `OPENAI_API_BASE` can be set to overwrite OpenAI API endpoint.")
                        with gr.Row(equal_height=True):
                            model = gr.Dropdown(
                                get_openai_supported_models(),
                                label="Model",
                                interactive=True,
                                allow_custom_value=True
                            )
                            voices = gr.Dropdown(
                                get_openai_supported_voices(),
                                label="Voice",
                                interactive=True,
                                allow_custom_value=True
                            )
                            speed = gr.Slider(
                                minimum=0.25,
                                maximum=4.0,
                                step=0.1,
                                label="Speed",
                                value=1.0,
                                info="Speed of the speech, 1.0 is normal speed"
                            )
                            openai_output_format = gr.Dropdown(
                                get_openai_supported_output_formats(),
                                label="Output Format",
                                interactive=True
                            )
                        instructions = gr.TextArea(
                            label="Voice Instructions",
                            interactive=True,
                            lines=3,
                            value=get_openai_instructions_example()
                        )
                        open_ai_tab.select(on_tab_change, inputs=None, outputs=None)

                    with gr.Tab("Azure", id="azure_tab_id") as azure_tab:
                        gr.Markdown("在此配置 Azure TTS 相关参数。若留空，将尝试读取环境变量 `MS_TTS_KEY` 与 `MS_TTS_REGION`。")
                        with gr.Row(equal_height=True):
                            azure_api_key = gr.Textbox(
                                label="Azure TTS Key (MS_TTS_KEY)",
                                value=os.environ.get("MS_TTS_KEY", ""),
                                placeholder="Automatically saved to browser storage",
                                type="password",
                                interactive=True,
                                elem_id="azure_api_key",
                            )
                            azure_region = gr.Textbox(
                                label="Azure 区域 (MS_TTS_REGION)",
                                value=os.environ.get("MS_TTS_REGION", ""),
                                placeholder="Automatically saved to browser storage",
                                interactive=True,
                                elem_id="azure_region",
                            )
                        with gr.Row(equal_height=True):
                            azure_language = gr.Dropdown(
                                get_azure_supported_languages(),
                                value="zh-CN",
                                label="Language",
                                interactive=True,
                                info="Select source language"
                            )
                            azure_voice = get_azure_voices_by_language("zh-CN")
                            azure_output_format = gr.Dropdown(
                                get_azure_supported_output_formats(),
                                label="Output Format",
                                interactive=True,
                                value="audio-48khz-96kbitrate-mono-mp3",
                                info="Select output format"
                            )
                            azure_break_duration = gr.Slider(
                                minimum=0,
                                maximum=5000,
                                step=1,
                                label="Break Duration",
                                value=1250,
                                info="Break duration in milliseconds. Valid values range from 0 to 5000, default: 1250ms"
                            )
                            azure_language.change(
                                fn=get_azure_voices_by_language,
                                inputs=azure_language,
                                outputs=azure_voice,
                            )
                        azure_tab.select(on_tab_change, inputs=None, outputs=None)

                    with gr.Tab("Edge", id="edge_tab_id") as edge_tab:
                        with gr.Row(equal_height=True):
                            edge_language = gr.Dropdown(
                                get_edge_tts_supported_language(),
                                value="en-US",
                                label="Language",
                                interactive=True,
                                info="Select source language"
                            )
                            edge_voice = get_edge_voices_by_language(edge_language.value)
                            edge_output_format = gr.Dropdown(
                                get_edge_tts_supported_output_formats(),
                                label="Output Format",
                                interactive=True,
                                info="Select output format"
                            )
                            proxy = gr.Textbox(
                                label="Proxy",
                                value="",
                                interactive=True,
                                info="Optional proxy server for the TTS provider"
                            )
                            edge_voice_rate = gr.Slider(
                                minimum=-50,
                                maximum=100,
                                step=1,
                                label="Voice Rate",
                                value=0,
                                info="Speaking rate (speed) of the text."
                            )
                            edge_volume = gr.Slider(
                                minimum=-100,
                                maximum=100,
                                step=1,
                                label="Voice Volume",
                                value=0,
                                info="Volume level of the speaking voice."
                            )
                            edge_pitch = gr.Slider(
                                minimum=-100,
                                maximum=100,
                                step=1,
                                label="Voice Pitch",
                                value=0,
                                info="Baseline pitch tone for the text."
                            )
                            edge_break_duration = gr.Slider(
                                minimum=0,
                                maximum=5000,
                                step=1,
                                label="Break Duration",
                                value=1250,
                                info="Break duration in milliseconds. Valid values range from 0 to 5000, default: 1250ms"
                            )

                            edge_language.change(
                                fn=get_edge_voices_by_language,
                                inputs=edge_language,
                                outputs=edge_voice,
                            )
                        edge_tab.select(on_tab_change, inputs=None, outputs=None)

                    with gr.Tab("Gemini", id="gemini_tab_id") as gemini_tab:
                        gemini_tab.select(on_tab_change, inputs=None, outputs=None)

                        with gr.Row(equal_height=True):
                            gemini_model = gr.Dropdown(
                                get_gemini_supported_models(),
                                label="Model",
                                value="gemini-2.5-pro-preview-tts",
                                interactive=True,
                                allow_custom_value=True,
                            )
                            gemini_voice = gr.Dropdown(
                                get_gemini_supported_voices(),
                                label="Voice",
                                value="Kore",
                                interactive=True,
                                info="Select Gemini preview voice",
                            )
                            gemini_output_format = gr.Dropdown(
                                get_gemini_supported_output_formats(),
                                label="Output Format",
                                value="wav",
                                interactive=True,
                                info="Preferred final audio container",
                            )

                        gemini_api_key = gr.Textbox(
                            label="Gemini API Key (GOOGLE_API_KEY)",
                            value=os.environ.get("GOOGLE_API_KEY", ""),
                            placeholder="Automatically saved to browser storage",
                            type="password",
                            interactive=True,
                            elem_id="gemini_api_key",
                        )

                        with gr.Row(equal_height=True):
                            gemini_sample_rate = gr.Slider(
                                minimum=8000,
                                maximum=48000,
                                step=1000,
                                label="Sample Rate (Hz)",
                                value=24000,
                                info="Default: 24000 Hz",
                            )
                            gemini_channels = gr.Dropdown(
                                ["1", "2"],
                                label="Channels",
                                value="1",
                                interactive=True,
                                info="Gemini currently输出单声道",
                            )
                            gemini_temperature = gr.Slider(
                                minimum=0.0,
                                maximum=1.0,
                                step=0.01,
                                label="Temperature",
                                value=0.2,
                                info="越低越稳定，0.0 表示几乎无随机性",
                            )

                        gemini_speaker_map = gr.TextArea(
                            label="Speaker Voice Map (JSON)",
                            placeholder='{"Narrator": "Kore", "Hero": "Puck"}',
                            lines=3,
                            interactive=True,
                            info="Optional: map speaker names in your prompt to Gemini voices",
                        )

                        gemini_instructions = gr.TextArea(
                            label="Style Instructions",
                            placeholder="Optional: e.g. 'Narrate warmly with a steady pace.'",
                            lines=3,
                            interactive=True,
                        )

                    with gr.Tab("Qwen3", id="qwen_tab_id") as qwen_tab:
                        qwen_tab.select(on_tab_change, inputs=None, outputs=None)

                        qwen_api_key = gr.Textbox(
                            label="DashScope API Key (DASHSCOPE_API_KEY)",
                            value=os.environ.get("DASHSCOPE_API_KEY", ""),
                            placeholder="Automatically saved to browser storage",
                            type="password",
                            interactive=True,
                            elem_id="qwen_api_key",
                        )

                        with gr.Row(equal_height=True):
                            qwen_model = gr.Dropdown(
                                get_qwen_supported_models(),
                                label="Model",
                                value="qwen3-tts-flash",
                                interactive=True,
                                allow_custom_value=True,
                                info="Select DashScope model snapshot",
                            )
                            qwen_voice = gr.Dropdown(
                                get_qwen_supported_voices(),
                                label="Voice",
                                value="Cherry",
                                interactive=True,
                                allow_custom_value=True,
                                info="Pick a Qwen3 voice",
                            )
                            qwen_language_type = gr.Dropdown(
                                get_qwen_supported_language_types(),
                                label="Language Type",
                                value="Chinese",
                                interactive=True,
                                info="Matches the text language for better pronunciation",
                            )

                        with gr.Row(equal_height=True):
                            qwen_locale = gr.Textbox(
                                label="Source Locale",
                                value="zh-CN",
                                interactive=True,
                                info="Used for splitting heuristics (e.g. zh-CN, en-US)",
                            )
                            qwen_stream = gr.Checkbox(
                                label="Enable Streaming",
                                value=False,
                                info="Collect streaming chunks instead of single URL fetch",
                            )
                            qwen_request_timeout = gr.Slider(
                                minimum=5,
                                maximum=120,
                                step=1,
                                label="Download Timeout (s)",
                                value=30,
                                info="Timeout when downloading audio URL",
                            )

                    with gr.Tab("Piper", id="piper_tab_id") as piper_tab:
                        piper_tab.select(on_tab_change, inputs=None, outputs=None)
                        with gr.Row(equal_height=True):
                            with gr.Column():
                                piper_deployment = gr.Dropdown(
                                    ["Docker", "Local"],
                                    label="Select Piper Deployment",
                                    interactive=True
                                )

                                local_group = gr.Group(visible=False)
                                with local_group:
                                    piper_executable_path = gr.Textbox(
                                        label="Piper executable path",
                                        interactive=True
                                    )
                                    piper_file_upload = gr.File(
                                        label="Upload Piper executable",
                                        file_count="single",
                                        interactive=True
                                    )
                                    piper_file_upload.change(
                                        fn=lambda x: x.name if x else "",
                                        inputs=piper_file_upload,
                                        outputs=piper_executable_path
                                    )

                                docker_group = gr.Row(visible=True, equal_height=True)
                                with docker_group:
                                    piper_docker_image = gr.Textbox(
                                        label="Piper Docker Image",
                                        value="lscr.io/linuxserver/piper:latest",
                                        interactive=True
                                    )

                            piper_deployment.change(
                                fn=lambda x: (gr.update(visible=x == "Local"), gr.update(visible=x == "Docker")),
                                inputs=piper_deployment,
                                outputs=[local_group, docker_group]
                            )

                            with gr.Column():
                                with gr.Row(equal_height=True):
                                    piper_language = gr.Dropdown(
                                        get_piper_supported_languages(),
                                        label="Language",
                                        value="en_US",
                                        interactive=True,
                                        info="Select language"
                                    )
                                    piper_voice = gr.Dropdown(
                                        get_piper_supported_voices(piper_language.value),
                                        label="Voice",
                                        interactive=True,
                                        info="Select voice"
                                    )
                                with gr.Row(equal_height=True):
                                    piper_quality = gr.Dropdown(
                                        get_piper_supported_qualities(piper_language.value, piper_voice.value),
                                        label="Quality",
                                        interactive=True,
                                        info="Select quality"
                                    )
                                    piper_speaker = gr.Dropdown(
                                        get_piper_supported_speakers(piper_language.value, piper_voice.value, piper_quality.value),
                                        label="Speaker",
                                        interactive=True,
                                        info="Select speaker if available"
                                    )

                            piper_language.change(
                                fn=get_piper_supported_voices_gui,
                                inputs=piper_language,
                                outputs=piper_voice,
                            )

                            piper_voice.change(
                                fn=get_piper_supported_qualities_gui,
                                inputs=[piper_language, piper_voice],
                                outputs=piper_quality,
                            )

                            piper_quality.change(
                                fn=get_piper_supported_speakers_gui,
                                inputs=[piper_language, piper_voice, piper_quality],
                                outputs=piper_speaker,
                            )

                            with gr.Column():
                                with gr.Row(equal_height=True):
                                    piper_noise_scale = gr.Slider(
                                        minimum=0.0,
                                        maximum=2.0,
                                        step=0.01,
                                        label="Audio Noise Scale",
                                        value=0.667
                                    )
                                    piper_noise_w_scale = gr.Slider(
                                        minimum=0.0,
                                        maximum=2.0,
                                        step=0.1,
                                        label="Width Noise Scale",
                                        value=0.8
                                    )
                                with gr.Row(equal_height=True):
                                    piper_length_scale = gr.Slider(
                                        minimum=0.0,
                                        maximum=5.0,
                                        step=0.1,
                                        label="Audio Length Scale",
                                        value=1.0
                                    )
                                    piper_sentence_silence = gr.Slider(
                                        minimum=0.0,
                                        maximum=2.0,
                                        step=0.1,
                                        label="Sentence Silence",
                                        value=0.2
                                    )


            with gr.Column(scale=4, min_width=420, elem_classes="setup-pane"):
                gr.Markdown("## 输入设置")
                input_file = gr.File(
                    label="书籍文件",
                    file_types=[".epub", ".md", ".markdown"],
                    file_count="single",
                    interactive=True,
                )

                gr.Markdown("## 文本处理")
                chinese_conversion = gr.Dropdown(
                    get_chinese_conversion_choices(),
                    label="繁简转换",
                    value="None",
                    interactive=True,
                )
                with gr.Accordion("高级设置：文本解析与章节范围", open=False):
                    with gr.Row(equal_height=True):
                        search_and_replace_file = gr.File(
                            label="发音替换文件（可选）",
                            file_types=[".txt"],
                            file_count="single",
                            interactive=True,
                        )
                        title_mode = gr.Dropdown(
                            ["auto", "tag_text", "first_few"],
                            label="标题识别",
                            value="auto",
                            interactive=True,
                            info="建议保持 auto，EPUB 会优先使用真实目录标题。"
                        )
                        new_line_mode = gr.Dropdown(
                            ["single", "double", "none"],
                            label="段落识别",
                            value="double",
                            interactive=True,
                            info="大多数书籍保持 double 即可。"
                        )
                    with gr.Row(equal_height=True):
                        chapter_start = gr.Slider(
                            minimum=1,
                            maximum=100,
                            step=1,
                            label="起始章节",
                            value=1,
                            interactive=True,
                            info="从第几章开始生成。"
                        )
                        chapter_end = gr.Slider(
                            minimum=-1,
                            maximum=100,
                            step=1,
                            label="结束章节",
                            value=-1,
                            interactive=True,
                            info="-1 表示生成到最后一章。"
                        )
                        with gr.Column():
                            remove_endnotes = gr.Checkbox(
                                label="移除尾注",
                                value=False,
                                info="适合学术类书籍。"
                            )
                            remove_reference_numbers = gr.Checkbox(
                                label="移除引用编号",
                                value=False,
                                info="移除类似 [3]、[12.1] 的引用编号。"
                            )

                with gr.Accordion("高级设置：运行与诊断", open=False):
                    with gr.Row(equal_height=True):
                        worker_count = gr.Slider(
                            minimum=1,
                            maximum=8,
                            step=1,
                            label="并发任务数",
                            value=1,
                            info="并发越高越快，但更容易触发服务限流或网络失败。"
                        )
                        log_level = gr.Dropdown(
                            ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"],
                            label="日志级别",
                            value="INFO",
                            interactive=True,
                            info="排查问题时可切换到 DEBUG。"
                        )

                gr.Markdown("## 输出设置")
                with gr.Row(equal_height=True):
                    output_dir = gr.Textbox(
                        label="输出目录",
                        value=default_output_dir,
                        interactive=True,
                        scale=2,
                    )
                    minimax_output_format = gr.Dropdown(
                        ["mp3", "wav"],
                        label="音频格式",
                        value="mp3",
                        interactive=True,
                        scale=1,
                    )
                with gr.Row(equal_height=True):
                    preview = gr.Checkbox(
                        label="预览解析与费用估算",
                        value=False,
                    )
                    export_m4b = gr.Checkbox(
                        label="额外导出单个 M4B",
                        value=False,
                    )
                    output_text = gr.Checkbox(
                        label="同时导出章节文本",
                        value=False,
                    )

                with gr.Row(equal_height=True, elem_classes="action-row"):
                    gr.Button("开始制作", variant="primary").click(
                        fn=process_ui_form,
                        inputs=[
                            input_file, output_dir, worker_count, log_level, output_text, preview, export_m4b,
                            search_and_replace_file, title_mode, new_line_mode, chinese_conversion, chapter_start, chapter_end, remove_endnotes, remove_reference_numbers,
                            azure_api_key, azure_region,
                            model, voices, speed, openai_output_format, instructions,
                            azure_language, azure_voice, azure_output_format, azure_break_duration,
                            edge_language, edge_voice, edge_output_format, proxy, edge_voice_rate, edge_volume, edge_pitch, edge_break_duration,
                            gemini_api_key, gemini_model, gemini_voice, gemini_output_format, gemini_sample_rate, gemini_channels, gemini_temperature, gemini_speaker_map, gemini_instructions,
                            qwen_api_key, qwen_model, qwen_voice, qwen_language_type, qwen_locale, qwen_stream, qwen_request_timeout,
                            minimax_api_key, minimax_model, minimax_voice, minimax_output_format, minimax_speed, minimax_volume, minimax_pitch, minimax_language_boost, minimax_request_timeout, minimax_narration_preset, minimax_heading_pause_duration, minimax_paragraph_pause_duration, minimax_section_break_pause_duration, minimax_chapter_ending_silence_duration,
                            piper_executable_path, piper_docker_image, piper_language, piper_voice, piper_quality, piper_speaker,
                            piper_noise_scale, piper_noise_w_scale, piper_length_scale, piper_sentence_silence
                        ],
                        outputs=None
                    )
                    gr.Button("停止当前任务").click(
                        fn=terminate_audiobook_generator,
                        inputs=None,
                        outputs=None
                    )


        with gr.Accordion("运行日志", open=False):
            with gr.Row():
                global webui_log_file
                webui_log_file = generate_unique_log_path("EtA_WebUI")
                webui_log_file.touch()
                Log(str(webui_log_file.absolute()), dark=True, xterm_font_size=12)

        gr.Markdown("---")
        with gr.Row():
            gr.Markdown('<span class="footer-hint">API Keys 会保存到浏览器本地存储，刷新页面后自动填充。</span>')
            clear_storage_btn = gr.Button("清除保存的 API Keys", size="sm", variant="secondary")

        # Add button click handler using Gradio's JavaScript
        clear_storage_btn.click(
            None,
            None,
            None,
            js="""
            function() {
                if (confirm('确定要清除所有保存的 API Keys 吗？')) {
                    localStorage.removeItem('FAL_KEY');
                    localStorage.removeItem('GOOGLE_API_KEY');
                    localStorage.removeItem('DASHSCOPE_API_KEY');
                    localStorage.removeItem('MS_TTS_KEY');
                    localStorage.removeItem('MS_TTS_REGION');
                    alert('已清除所有保存的 API Keys！刷新页面后输入框将为空。');
                    location.reload();
                }
            }
            """
        )

    ui.launch(server_name=config.host, server_port=config.port)
