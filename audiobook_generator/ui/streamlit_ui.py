from __future__ import annotations

from datetime import datetime
from multiprocessing import Process
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st

from audiobook_generator.config.general_config import GeneralConfig
from audiobook_generator.tts_providers.azure_tts_provider import (
    get_azure_supported_languages,
    get_azure_supported_output_formats,
    get_azure_supported_voices,
)
from audiobook_generator.tts_providers.edge_tts_provider import (
    get_edge_tts_supported_language,
    get_edge_tts_supported_output_formats,
    get_edge_tts_supported_voices,
)
from audiobook_generator.tts_providers.gemini_tts_provider import (
    get_gemini_supported_models,
    get_gemini_supported_output_formats,
    get_gemini_supported_voices,
)
from audiobook_generator.tts_providers.minimax_tts_provider import (
    get_minimax_supported_language_boosts,
    get_minimax_supported_models,
    get_minimax_supported_voice_display_names,
    resolve_minimax_voice_id,
)
from audiobook_generator.tts_providers.openai_tts_provider import (
    get_openai_instructions_example,
    get_openai_supported_models,
    get_openai_supported_output_formats,
    get_openai_supported_voices,
)
from audiobook_generator.tts_providers.piper_tts_provider import (
    get_piper_supported_languages,
    get_piper_supported_qualities,
    get_piper_supported_speakers,
    get_piper_supported_voices,
)
from audiobook_generator.tts_providers.qwen_tts_provider import (
    get_qwen_supported_language_types,
    get_qwen_supported_models,
    get_qwen_supported_voices,
)
from audiobook_generator.utils.chinese_conversion import get_chinese_conversion_choices
from audiobook_generator.utils.heading_pause import (
    get_minimax_narration_preset_values,
    get_narration_rhythm_preset_choices,
)
from audiobook_generator.utils.log_handler import generate_unique_log_path
from main import main as run_generator


UPLOAD_DIR = Path(".streamlit_uploads")

PROVIDER_CONFIGS = {
    "MiniMax": {"tts": "minimax", "formats": ["mp3", "wav"], "default_format": "mp3"},
    "OpenAI": {
        "tts": "openai",
        "formats": get_openai_supported_output_formats(),
        "default_format": "mp3",
    },
    "Azure": {
        "tts": "azure",
        "formats": get_azure_supported_output_formats(),
        "default_format": "audio-48khz-96kbitrate-mono-mp3",
    },
    "Edge": {"tts": "edge", "formats": get_edge_tts_supported_output_formats(), "default_format": "mp3"},
    "Gemini": {
        "tts": "gemini",
        "formats": get_gemini_supported_output_formats(),
        "default_format": "wav",
    },
    "Qwen3": {"tts": "qwen3", "formats": ["wav"], "default_format": "wav"},
    "Piper": {"tts": "piper", "formats": ["mp3", "wav"], "default_format": "mp3"},
}

CHINESE_CONVERSION_DISPLAY_LABELS = {
    "None": "不转换",
    "Traditional to Simplified": "繁体转简体",
    "Taiwan Traditional to Simplified": "台湾繁体转简体",
    "Taiwan Traditional to Simplified with Mainland phrases": "台湾繁体转简体（大陆词汇）",
}


def run_app() -> None:
    st.set_page_config(page_title="Reson", page_icon=None, layout="centered")
    _inject_style()
    _init_session_state()

    st.title("Reson")
    st.caption("Before words, there was voice.")

    provider, provider_values = _render_engine_sidebar()

    input_values = _render_input_section()
    text_values = _render_text_section()
    output_values = _render_output_section(provider)
    runtime_values = _current_runtime_values()
    _render_actions(provider, provider_values, input_values, text_values, output_values, runtime_values)
    _render_logs()


def _inject_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --reson-paper: #fbfaf7;
            --reson-sidebar: #eef1f5;
            --reson-surface: #ffffff;
            --reson-surface-raised: #fffdf9;
            --reson-surface-subtle: #f1f3f7;
            --reson-ink: #252838;
            --reson-secondary: #5f6472;
            --reson-muted: #858b99;
            --reson-border: #d9d6cf;
            --reson-border-strong: #bdb7aa;
            --reson-brand: #d59b48;
            --reson-brand-strong: #b77927;
            --reson-accent: #e8c48b;
            --reson-accent-soft: #f5ead8;
            --reson-focus: rgba(213, 155, 72, 0.28);
        }
        html,
        body,
        [data-testid="stAppViewContainer"] {
            background: var(--reson-paper);
            color: var(--reson-ink);
        }
        [data-testid="stHeader"] {
            background: transparent;
        }
        .block-container {
            width: min(640px, calc(100vw - 10rem));
            max-width: 640px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
            padding-top: 2.5rem;
            padding-bottom: 3rem;
        }
        @media (min-width: 1600px) {
            .block-container {
                width: min(640px, calc(100vw - 16rem));
                max-width: 640px !important;
            }
        }
        h1 {
            color: var(--reson-ink);
            font-size: clamp(2.8rem, 7vw, 4.5rem);
            font-weight: 800;
            letter-spacing: 0;
            margin-bottom: 0.1rem;
            line-height: 1;
        }
        h2, h3 {
            color: var(--reson-ink);
            letter-spacing: 0;
        }
        p, label, span {
            letter-spacing: 0;
        }
        div[data-testid="stCaptionContainer"] {
            color: var(--reson-muted);
            font-size: 1.02rem;
        }
        [data-testid="stMarkdownContainer"] h4 {
            color: var(--reson-ink);
            font-size: 1.45rem;
            line-height: 1.15;
            margin: 0.9rem 0 0.75rem;
        }
        hr {
            border-color: rgba(37, 40, 56, 0.12);
            margin: 1.5rem 0 1.2rem;
        }
        section[data-testid="stSidebar"] {
            background: var(--reson-sidebar);
            border-right: 1px solid rgba(148, 135, 112, 0.28);
        }
        div[data-testid="stSidebarHeader"] {
            padding-bottom: 0.5rem;
        }
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: var(--reson-ink);
        }
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        section[data-testid="stSidebar"] label {
            color: var(--reson-ink);
        }
        div[data-baseweb="select"] > div,
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        textarea {
            background-color: var(--reson-surface);
            border-color: rgba(37, 40, 56, 0.12);
            border-radius: 10px;
            color: var(--reson-ink);
        }
        div[data-baseweb="select"] > div:hover,
        div[data-testid="stTextInput"] input:hover,
        div[data-testid="stNumberInput"] input:hover,
        textarea:hover {
            border-color: var(--reson-border-strong);
        }
        div[data-baseweb="select"] > div:focus-within,
        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stNumberInput"] input:focus,
        textarea:focus {
            border-color: var(--reson-brand);
            box-shadow: 0 0 0 3px var(--reson-focus);
        }
        div[data-testid="stFileUploaderDropzone"] {
            background: var(--reson-surface-subtle);
            border: 1px solid rgba(37, 40, 56, 0.1);
            border-radius: 14px;
            min-height: 76px;
        }
        div[data-testid="stFileUploaderDropzone"]:hover {
            border-color: var(--reson-brand);
            background: #f7f2ea;
        }
        div[data-testid="stExpander"] details {
            background: var(--reson-surface-raised);
            border-color: var(--reson-border);
            border-radius: 10px;
        }
        div[data-testid="stExpander"] summary {
            color: var(--reson-ink);
            font-weight: 650;
        }
        .stButton button[kind="primary"] {
            background: var(--reson-accent);
            color: #16110b;
            border-color: var(--reson-accent);
            border-radius: 10px;
            font-weight: 700;
        }
        .stButton button[kind="primary"]:hover {
            background: #f0d3a2;
            color: #16110b;
            border-color: #f0d3a2;
        }
        .stButton button[kind="secondary"] {
            background: var(--reson-surface);
            border-color: var(--reson-border);
            border-radius: 10px;
            color: var(--reson-secondary);
        }
        .stButton button[kind="secondary"]:hover {
            border-color: var(--reson-border-strong);
            color: var(--reson-ink);
        }
        .stSlider [data-baseweb="slider"] {
            padding-top: 0.65rem;
        }
        .stSlider [data-baseweb="slider"] div[role="slider"] {
            background-color: var(--reson-brand);
            border-color: var(--reson-brand);
            box-shadow: 0 0 0 4px rgba(213, 155, 72, 0.14);
        }
        .stSlider [data-baseweb="slider"] div[role="slider"]:focus,
        .stSlider [data-baseweb="slider"] div[role="slider"]:hover {
            box-shadow: 0 0 0 6px var(--reson-focus);
        }
        .stSlider [data-baseweb="slider"] div[role="slider"]::before {
            background: var(--reson-brand);
        }
        .stSlider [data-baseweb="slider"] > div > div {
            background-color: #dfe4ec;
        }
        .stSlider [data-baseweb="slider"] div[style*="background: rgb(255, 75, 75)"],
        .stSlider [data-baseweb="slider"] div[style*="background-color: rgb(255, 75, 75)"],
        .stSlider [data-baseweb="slider"] div[style*="background: rgb(255, 76, 76)"],
        .stSlider [data-baseweb="slider"] div[style*="background-color: rgb(255, 76, 76)"] {
            background: var(--reson-brand) !important;
            background-color: var(--reson-brand) !important;
        }
        [data-testid="stCheckbox"] label {
            gap: 0.45rem;
        }
        [data-testid="stAlert"] {
            border-radius: 10px;
        }
        code {
            border-radius: 10px;
        }
        @media (max-width: 720px) {
            .block-container {
                width: calc(100vw - 2rem);
                padding: 1.25rem 1rem 2rem;
            }
            [data-testid="stMarkdownContainer"] h4 {
                font-size: 1.45rem;
            }
            div[data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
            }
            div[data-testid="stFileUploaderDropzone"] {
                min-height: 68px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _init_session_state() -> None:
    if "default_output_dir" not in st.session_state:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        st.session_state.default_output_dir = os.path.join("audiobook_output", timestamp)

    if "streamlit_log_file" not in st.session_state:
        log_file = generate_unique_log_path("EtA_Streamlit").absolute()
        log_file.touch(exist_ok=True)
        st.session_state.streamlit_log_file = str(log_file)

    if "running_process" not in st.session_state:
        st.session_state.running_process = None

    if "runtime_worker_count" not in st.session_state:
        st.session_state.runtime_worker_count = 1

    if "runtime_log_level" not in st.session_state:
        st.session_state.runtime_log_level = "INFO"


def _render_engine_sidebar() -> tuple[str, dict[str, Any]]:
    with st.sidebar:
        st.header("声音处理引擎")
        provider = st.selectbox(
            "TTS 供应商",
            list(PROVIDER_CONFIGS.keys()),
            index=0,
            key="tts_provider",
        )
        st.divider()

        if provider == "MiniMax":
            values = _render_minimax_controls()
        elif provider == "OpenAI":
            values = _render_openai_controls()
        elif provider == "Azure":
            values = _render_azure_controls()
        elif provider == "Edge":
            values = _render_edge_controls()
        elif provider == "Gemini":
            values = _render_gemini_controls()
        elif provider == "Qwen3":
            values = _render_qwen_controls()
        elif provider == "Piper":
            values = _render_piper_controls()
        else:
            values = {}

    return provider, values


def _render_minimax_controls() -> dict[str, Any]:
    api_key = st.text_input(
        "MiniMax / FAL API Key",
        value=os.environ.get("FAL_KEY", ""),
        type="password",
        key="minimax_api_key",
    )
    model = _selectbox(
        "模型",
        get_minimax_supported_models(),
        default="fal-ai/minimax/speech-2.8-hd",
        key="minimax_model_latest",
    )
    voice = _selectbox(
        "朗读声音",
        get_minimax_supported_voice_display_names(),
        default="温暖闺蜜",
        key="minimax_voice_display",
    )
    language_boost = _selectbox(
        "语言增强",
        ["不指定"] + get_minimax_supported_language_boosts(),
        default="不指定",
        key="minimax_language_boost",
    )
    speed = st.slider("语速", 0.5, 2.0, 1.0, 0.1, key="minimax_speed")
    pitch = st.slider("音高", -12, 12, 0, 1, key="minimax_pitch")

    with st.expander("MiniMax 专业参数", expanded=False):
        rhythm = _selectbox(
            "朗读节奏",
            get_narration_rhythm_preset_choices(),
            default="Natural",
            key="minimax_rhythm",
        )
        defaults = get_minimax_narration_preset_values(rhythm)
        volume = st.slider("音量", 0.1, 2.0, 1.0, 0.1, key="minimax_volume")
        timeout = st.slider("下载超时（秒）", 10, 180, 60, 5, key="minimax_timeout")
        heading_pause = st.slider(
            "标题后停顿（秒）",
            0.0,
            5.0,
            float(defaults["heading"]),
            0.1,
            key=f"minimax_heading_pause_{rhythm}",
        )
        paragraph_pause = st.slider(
            "段落停顿（秒）",
            0.0,
            2.0,
            float(defaults["paragraph"]),
            0.05,
            key=f"minimax_paragraph_pause_{rhythm}",
        )
        section_break_pause = st.slider(
            "小节停顿（秒）",
            0.0,
            5.0,
            float(defaults["section_break"]),
            0.1,
            key=f"minimax_section_pause_{rhythm}",
        )
        chapter_ending_silence = st.slider(
            "章节结尾留白（秒）",
            0.0,
            5.0,
            float(defaults["chapter_ending"]),
            0.1,
            key=f"minimax_chapter_silence_{rhythm}",
        )

    return {
        "api_key": api_key,
        "model": model,
        "voice": resolve_minimax_voice_id(voice),
        "language_boost": None if language_boost == "不指定" else language_boost,
        "speed": speed,
        "pitch": pitch,
        "volume": volume,
        "timeout": timeout,
        "rhythm": rhythm,
        "heading_pause": heading_pause,
        "paragraph_pause": paragraph_pause,
        "section_break_pause": section_break_pause,
        "chapter_ending_silence": chapter_ending_silence,
    }


def _render_openai_controls() -> dict[str, Any]:
    model = _selectbox(
        "模型",
        get_openai_supported_models(),
        default="gpt-4o-mini-tts",
        key="openai_model",
    )
    voice = _selectbox(
        "朗读声音",
        get_openai_supported_voices(),
        default="alloy",
        key="openai_voice",
    )
    speed = st.slider("语速", 0.25, 4.0, 1.0, 0.1, key="openai_speed")
    with st.expander("OpenAI 专业参数", expanded=False):
        instructions = st.text_area(
            "朗读指令",
            value=get_openai_instructions_example(),
            height=180,
            key="openai_instructions",
        )
    return {"model": model, "voice": voice, "speed": speed, "instructions": instructions}


def _render_azure_controls() -> dict[str, Any]:
    api_key = st.text_input(
        "Azure TTS Key",
        value=os.environ.get("MS_TTS_KEY", ""),
        type="password",
        key="azure_api_key",
    )
    region = st.text_input("Azure 区域", value=os.environ.get("MS_TTS_REGION", ""), key="azure_region")
    language = _selectbox(
        "语言",
        get_azure_supported_languages(),
        default="zh-CN",
        key="azure_language",
    )
    voices = _voices_for_language(get_azure_supported_voices(), language)
    voice = _selectbox("朗读声音", voices, default="zh-CN-XiaoxiaoMultilingualNeural", key="azure_voice")
    break_duration = st.slider("段落停顿（毫秒）", 0, 5000, 1250, 50, key="azure_break")
    return {
        "api_key": api_key,
        "region": region,
        "language": language,
        "voice": voice,
        "break_duration": break_duration,
    }


def _render_edge_controls() -> dict[str, Any]:
    language = _selectbox(
        "语言",
        get_edge_tts_supported_language(),
        default="zh-CN",
        key="edge_language",
    )
    voices = _voices_for_language(get_edge_tts_supported_voices(), language)
    voice = _selectbox("朗读声音", voices, default=voices[0] if voices else None, key="edge_voice")
    with st.expander("Edge 专业参数", expanded=False):
        proxy = st.text_input("代理", value="", key="edge_proxy")
        rate = st.slider("语速调整（%）", -50, 100, 0, 1, key="edge_rate")
        volume = st.slider("音量调整（%）", -100, 100, 0, 1, key="edge_volume")
        pitch = st.slider("音高调整（Hz）", -100, 100, 0, 1, key="edge_pitch")
        break_duration = st.slider("段落停顿（毫秒）", 0, 5000, 1250, 50, key="edge_break")
    return {
        "language": language,
        "voice": voice,
        "proxy": proxy,
        "rate": rate,
        "volume": volume,
        "pitch": pitch,
        "break_duration": break_duration,
    }


def _render_gemini_controls() -> dict[str, Any]:
    api_key = st.text_input(
        "Gemini API Key",
        value=os.environ.get("GOOGLE_API_KEY", ""),
        type="password",
        key="gemini_api_key",
    )
    model = _selectbox(
        "模型",
        get_gemini_supported_models(),
        default="gemini-2.5-pro-preview-tts",
        key="gemini_model",
    )
    voice = _selectbox(
        "朗读声音",
        get_gemini_supported_voices(),
        default="Kore",
        key="gemini_voice",
    )
    with st.expander("Gemini 专业参数", expanded=False):
        sample_rate = st.slider("采样率（Hz）", 8000, 48000, 24000, 1000, key="gemini_sample_rate")
        channels = st.selectbox("声道", ["1", "2"], index=0, key="gemini_channels")
        temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.01, key="gemini_temperature")
        speaker_map = st.text_area("Speaker Voice Map (JSON)", value="", height=100, key="gemini_speaker_map")
        instructions = st.text_area("风格指令", value="", height=100, key="gemini_instructions")
    return {
        "api_key": api_key,
        "model": model,
        "voice": voice,
        "sample_rate": sample_rate,
        "channels": channels,
        "temperature": temperature,
        "speaker_map": speaker_map,
        "instructions": instructions,
    }


def _render_qwen_controls() -> dict[str, Any]:
    api_key = st.text_input(
        "DashScope API Key",
        value=os.environ.get("DASHSCOPE_API_KEY", ""),
        type="password",
        key="qwen_api_key",
    )
    model = _selectbox("模型", get_qwen_supported_models(), default="qwen3-tts-flash", key="qwen_model")
    voice = _selectbox("朗读声音", get_qwen_supported_voices(), default="Cherry", key="qwen_voice")
    language_type = _selectbox(
        "语言类型",
        get_qwen_supported_language_types(),
        default="Chinese",
        key="qwen_language_type",
    )
    with st.expander("Qwen3 专业参数", expanded=False):
        locale = st.text_input("文本语言", value="zh-CN", key="qwen_locale")
        stream = st.checkbox("启用流式响应", value=False, key="qwen_stream")
        timeout = st.slider("下载超时（秒）", 5, 120, 30, 1, key="qwen_timeout")
    return {
        "api_key": api_key,
        "model": model,
        "voice": voice,
        "language_type": language_type,
        "locale": locale,
        "stream": stream,
        "timeout": timeout,
    }


def _render_piper_controls() -> dict[str, Any]:
    deployment = st.selectbox("部署方式", ["Docker", "Local"], index=0, key="piper_deployment")
    executable_path = ""
    docker_image = "lscr.io/linuxserver/piper:latest"
    if deployment == "Local":
        executable_path = st.text_input("Piper executable path", value="piper", key="piper_path")
    else:
        docker_image = st.text_input("Piper Docker Image", value=docker_image, key="piper_docker_image")

    language = _selectbox("语言", get_piper_supported_languages(), default="en_US", key="piper_language")
    voices = get_piper_supported_voices(language)
    voice = _selectbox("朗读声音", voices, default=voices[0], key="piper_voice")
    qualities = get_piper_supported_qualities(language, voice)
    quality = _selectbox("质量", qualities, default=qualities[0], key="piper_quality")
    speakers = [str(speaker) for speaker in get_piper_supported_speakers(language, voice, quality)]
    speaker = _selectbox("Speaker", speakers, default=speakers[0], key="piper_speaker")

    with st.expander("Piper 专业参数", expanded=False):
        noise_scale = st.slider("Audio Noise Scale", 0.0, 2.0, 0.667, 0.01, key="piper_noise_scale")
        noise_w_scale = st.slider("Width Noise Scale", 0.0, 2.0, 0.8, 0.1, key="piper_noise_w_scale")
        length_scale = st.slider("Audio Length Scale", 0.0, 5.0, 1.0, 0.1, key="piper_length_scale")
        sentence_silence = st.slider("Sentence Silence", 0.0, 2.0, 0.2, 0.1, key="piper_sentence_silence")

    return {
        "deployment": deployment,
        "executable_path": executable_path,
        "docker_image": docker_image,
        "language": language,
        "voice": voice,
        "quality": quality,
        "speaker": speaker,
        "noise_scale": noise_scale,
        "noise_w_scale": noise_w_scale,
        "length_scale": length_scale,
        "sentence_silence": sentence_silence,
    }


def _render_input_section() -> dict[str, Any]:
    st.markdown("#### 输入设置")
    uploaded_book = st.file_uploader("书籍文件", type=["epub", "md", "markdown"], key="book_file")
    return {"uploaded_book": uploaded_book}


def _render_text_section() -> dict[str, Any]:
    chinese_conversion_label = st.selectbox(
        "繁简转换",
        _get_chinese_conversion_display_choices(),
        index=0,
    )
    chinese_conversion = _resolve_chinese_conversion_value(chinese_conversion_label)

    with st.expander("高级设置：文本解析与章节范围", expanded=False):
        search_and_replace_file = st.file_uploader("发音替换文件（可选）", type=["txt"], key="replace_file")
        col_a, col_b = st.columns(2)
        with col_a:
            title_mode = st.selectbox("标题识别", ["auto", "tag_text", "first_few"], index=0)
        with col_b:
            newline_mode = st.selectbox("段落识别", ["single", "double", "none"], index=1)

        col_c, col_d = st.columns(2)
        with col_c:
            chapter_start = st.number_input("起始章节", min_value=1, max_value=9999, value=1, step=1)
        with col_d:
            chapter_end = st.number_input("结束章节", min_value=-1, max_value=9999, value=-1, step=1)

        remove_endnotes = st.checkbox("移除尾注", value=False)
        remove_reference_numbers = st.checkbox("移除引用编号", value=False)

    return {
        "chinese_conversion": chinese_conversion,
        "search_and_replace_file": search_and_replace_file,
        "title_mode": title_mode,
        "newline_mode": newline_mode,
        "chapter_start": int(chapter_start),
        "chapter_end": int(chapter_end),
        "remove_endnotes": remove_endnotes,
        "remove_reference_numbers": remove_reference_numbers,
    }


def _render_output_section(provider: str) -> dict[str, Any]:
    st.markdown("#### 输出设置")
    provider_config = PROVIDER_CONFIGS[provider]
    formats = list(provider_config["formats"])
    default_format = provider_config["default_format"]

    col_a, col_b = st.columns([3, 1])
    with col_a:
        output_dir = st.text_input("输出目录", value=st.session_state.default_output_dir)
    with col_b:
        output_format = _selectbox("音频格式", formats, default=default_format, key=f"{provider}_output_format")

    col_c, col_d, col_e = st.columns(3)
    with col_c:
        preview = st.checkbox("预览解析与费用估算", value=False)
    with col_d:
        export_m4b = st.checkbox("额外导出单个 M4B", value=False)
    with col_e:
        output_text = st.checkbox("同时导出章节文本", value=False)

    return {
        "output_dir": output_dir,
        "output_format": output_format,
        "preview": preview,
        "export_m4b": export_m4b,
        "output_text": output_text,
    }


def _current_runtime_values() -> dict[str, Any]:
    return {
        "worker_count": int(st.session_state.get("runtime_worker_count", 1)),
        "log_level": st.session_state.get("runtime_log_level", "INFO"),
    }


def _render_actions(
    provider: str,
    provider_values: dict[str, Any],
    input_values: dict[str, Any],
    text_values: dict[str, Any],
    output_values: dict[str, Any],
    runtime_values: dict[str, Any],
) -> None:
    proc = _active_process()
    if proc:
        st.info(f"当前任务运行中，PID: {proc.pid}")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        start_clicked = st.button("开始制作", type="primary", use_container_width=True, disabled=bool(proc))
    with col_b:
        stop_clicked = st.button("停止当前任务", use_container_width=True, disabled=not bool(proc))

    if stop_clicked:
        _terminate_process()
        st.success("已停止当前任务。")
        st.rerun()

    if not start_clicked:
        return

    if proc:
        st.warning("已有任务正在运行。")
        return

    uploaded_book = input_values["uploaded_book"]
    if uploaded_book is None:
        st.error("请先上传 EPUB 或 Markdown 文件。")
        return

    try:
        input_path = _save_uploaded_file(uploaded_book)
        replacement_path = _save_uploaded_file(text_values["search_and_replace_file"])
        config = _build_config(
            provider,
            provider_values,
            input_path,
            replacement_path,
            text_values,
            output_values,
            runtime_values,
        )
        log_file = st.session_state.streamlit_log_file
        process = Process(target=run_generator, args=(config, log_file))
        process.start()
        st.session_state.running_process = process
        st.success(f"任务已启动，PID: {process.pid}")
        st.rerun()
    except Exception as exc:
        st.error(f"启动失败：{exc}")


def _build_config(
    provider: str,
    provider_values: dict[str, Any],
    input_path: str,
    replacement_path: str | None,
    text_values: dict[str, Any],
    output_values: dict[str, Any],
    runtime_values: dict[str, Any],
) -> GeneralConfig:
    config = GeneralConfig(None)
    config.input_file = input_path
    config.output_folder = output_values["output_dir"]
    config.preview = output_values["preview"]
    config.output_text = output_values["output_text"]
    config.export_m4b = output_values["export_m4b"]
    config.output_format = output_values["output_format"]
    config.log = runtime_values["log_level"]
    config.worker_count = runtime_values["worker_count"]
    config.no_prompt = True
    config.use_pydub_merge = None

    config.title_mode = text_values["title_mode"]
    config.newline_mode = text_values["newline_mode"]
    config.chinese_conversion = text_values["chinese_conversion"]
    config.chapter_start = text_values["chapter_start"]
    config.chapter_end = text_values["chapter_end"]
    config.remove_endnotes = text_values["remove_endnotes"]
    config.remove_reference_numbers = text_values["remove_reference_numbers"]
    config.search_and_replace_file = replacement_path or ""

    tts_name = PROVIDER_CONFIGS[provider]["tts"]
    config.tts = tts_name

    if provider == "MiniMax":
        _set_env_if_present("FAL_KEY", provider_values["api_key"])
        config.model_name = provider_values["model"]
        config.voice_name = provider_values["voice"]
        config.language = "zh-CN"
        config.minimax_api_key = _clean(provider_values["api_key"])
        config.minimax_speed = float(provider_values["speed"])
        config.minimax_volume = float(provider_values["volume"])
        config.minimax_pitch = float(provider_values["pitch"])
        config.minimax_language_boost = provider_values["language_boost"]
        config.minimax_request_timeout = int(provider_values["timeout"])
        config.minimax_narration_preset = provider_values["rhythm"]
        config.minimax_heading_pause_duration = float(provider_values["heading_pause"])
        config.minimax_paragraph_pause_duration = float(provider_values["paragraph_pause"])
        config.minimax_section_break_pause_duration = float(provider_values["section_break_pause"])
        config.minimax_chapter_ending_silence_duration = float(provider_values["chapter_ending_silence"])
    elif provider == "OpenAI":
        config.model_name = provider_values["model"]
        config.voice_name = provider_values["voice"]
        config.language = "zh-CN"
        config.speed = float(provider_values["speed"])
        config.instructions = _clean(provider_values["instructions"])
    elif provider == "Azure":
        _set_env_if_present("MS_TTS_KEY", provider_values["api_key"])
        _set_env_if_present("MS_TTS_REGION", provider_values["region"])
        config.language = provider_values["language"]
        config.voice_name = provider_values["voice"]
        config.break_duration = int(provider_values["break_duration"])
    elif provider == "Edge":
        config.language = provider_values["language"]
        config.voice_name = provider_values["voice"]
        config.proxy = _clean(provider_values["proxy"])
        config.voice_rate = f"{provider_values['rate']:+}%"
        config.voice_volume = f"{provider_values['volume']:+}%"
        config.voice_pitch = f"{provider_values['pitch']:+}Hz"
        config.break_duration = int(provider_values["break_duration"])
    elif provider == "Gemini":
        _set_env_if_present("GOOGLE_API_KEY", provider_values["api_key"])
        config.model_name = provider_values["model"]
        config.voice_name = provider_values["voice"]
        config.language = "zh-CN"
        config.gemini_api_key = _clean(provider_values["api_key"])
        config.gemini_sample_rate = int(provider_values["sample_rate"])
        config.gemini_channels = int(provider_values["channels"])
        config.gemini_temperature = float(provider_values["temperature"])
        config.gemini_speaker_map = _clean(provider_values["speaker_map"])
        config.instructions = _clean(provider_values["instructions"])
    elif provider == "Qwen3":
        _set_env_if_present("DASHSCOPE_API_KEY", provider_values["api_key"])
        config.model_name = provider_values["model"]
        config.voice_name = provider_values["voice"]
        config.language = provider_values["locale"]
        config.qwen_api_key = _clean(provider_values["api_key"])
        config.qwen_language_type = provider_values["language_type"]
        config.qwen_stream = bool(provider_values["stream"])
        config.qwen_request_timeout = int(provider_values["timeout"])
    elif provider == "Piper":
        config.language = provider_values["language"]
        config.piper_path = provider_values["executable_path"] if provider_values["deployment"] == "Local" else ""
        config.piper_docker_image = provider_values["docker_image"]
        config.model_name = f"{provider_values['language']}-{provider_values['voice']}-{provider_values['quality']}"
        config.piper_speaker = provider_values["speaker"]
        config.piper_noise_scale = provider_values["noise_scale"]
        config.piper_noise_w_scale = provider_values["noise_w_scale"]
        config.piper_length_scale = provider_values["length_scale"]
        config.piper_sentence_silence = provider_values["sentence_silence"]

    return config


def _render_logs() -> None:
    log_file = Path(st.session_state.streamlit_log_file)
    with st.expander("运行日志", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            st.slider("并发任务数", 1, 8, 1, 1, key="runtime_worker_count")
        with col_b:
            st.selectbox(
                "日志级别",
                ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"],
                index=["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"].index(
                    st.session_state.get("runtime_log_level", "INFO")
                ),
                key="runtime_log_level",
            )
        st.caption(str(log_file))
        if st.button("刷新日志"):
            st.rerun()
        tail = _read_log_tail(log_file)
        st.code(tail or "暂无日志。", language="text")


def _active_process() -> Process | None:
    proc = st.session_state.get("running_process")
    if not proc:
        return None

    if proc.is_alive():
        return proc

    proc.join(timeout=0.1)
    st.session_state.running_process = None
    return None


def _terminate_process() -> None:
    proc = st.session_state.get("running_process")
    if proc and proc.is_alive():
        proc.terminate()
        proc.join(timeout=2)
    st.session_state.running_process = None


def _save_uploaded_file(uploaded_file) -> str | None:
    if uploaded_file is None:
        return None

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name
    path = UPLOAD_DIR / f"{uuid4().hex}_{safe_name}"
    path.write_bytes(uploaded_file.getvalue())
    return str(path)


def _read_log_tail(path: Path, lines: int = 200) -> str:
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


def _selectbox(label: str, options: list[Any], default: Any = None, key: str | None = None, **kwargs) -> Any:
    if not options:
        st.warning(f"{label} 暂无可选项。")
        return None
    index = options.index(default) if default in options else 0
    return st.selectbox(label, options, index=index, key=key, **kwargs)


def _voices_for_language(voices: list[str], language: str) -> list[str]:
    matches = [voice for voice in voices if voice.startswith(language)]
    return matches or voices


def _get_chinese_conversion_display_choices() -> list[str]:
    return [
        CHINESE_CONVERSION_DISPLAY_LABELS.get(choice, choice)
        for choice in get_chinese_conversion_choices()
    ]


def _resolve_chinese_conversion_value(display_label: str) -> str:
    for value, label in CHINESE_CONVERSION_DISPLAY_LABELS.items():
        if label == display_label:
            return value
    return display_label


def _set_env_if_present(name: str, value: str | None) -> None:
    cleaned = _clean(value)
    if cleaned:
        os.environ[name] = cleaned


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
