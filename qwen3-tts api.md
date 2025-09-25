支持的模型
推荐使用 Qwen3-TTS。

Qwen3-TTS 拥有 17种音色，支持多种语言及方言。

Qwen-TTS 仅拥有7种音色，且只支持中文和英文。

Qwen3-TTSQwen-TTS
模型名称

版本

单价

最大输入字符数

支持的语种

免费额度（注）

qwen3-tts-flash

当前能力等同 qwen3-tts-flash-2025-09-18
稳定版

0.8元/万字符

600

中文（普通话、北京、上海、四川、南京、陕西、闽南、天津、粤语）、英文、西班牙语、俄语、意大利语、法语、韩语、日语、德语、葡萄牙语

各2000字符

有效期：百炼开通后90天内

qwen3-tts-flash-2025-09-18

快照版

功能特性



功能特性

Qwen3-TTS

Qwen-TTS

接入方式

Python、Java、HTTP

流式输出

支持

流式输入

不支持

Qwen-TTS Realtime API 支持流式输入。
合成音频格式

wav

流式输出 Base64 编码的 pcm

合成音频采样率

24kHz

时间戳

不支持

语言

中文（普通话、北京、上海、四川、南京、陕西、闽南、天津、粤语）、英文、西班牙语、俄语、意大利语、法语、韩语、日语、德语、葡萄牙语，因音色而异，详情请参见支持的音色

中文（普通话、北京、上海、四川）、英文，因模型和音色而异，详情请参见支持的音色

声音复刻

不支持

SSML

不支持

快速开始
准备工作

已配置 API Key并配置API Key到环境变量。

如果通过 DashScope SDK 进行调用，需要安装最新版SDK。

DashScope Java SDK 版本需要不低于 2.21.9。

DashScope Python SDK 版本需要不低于 1.24.6，DashScope Python SDK中的SpeechSynthesizer接口已统一为MultiModalConversation，使用新接口只需替换接口名称即可，其他参数完全兼容。

可通过text指定文本，voice指定音色，通过返回的url来获取合成的语音。

URL 有效期为24 小时。
PythonJavacurl

 
#  DashScope SDK 版本不低于 1.24.6
import os
import requests
import dashscope

text = "那我来给大家推荐一款T恤，这款呢真的是超级好看，这个颜色呢很显气质，而且呢也是搭配的绝佳单品，大家可以闭眼入，真的是非常好看，对身材的包容性也很好，不管啥身材的宝宝呢，穿上去都是很好看的。推荐宝宝们下单哦。"
# SpeechSynthesizer接口使用方法：dashscope.audio.qwen_tts.SpeechSynthesizer.call(...)
response = dashscope.MultiModalConversation.call(
    model="qwen3-tts-flash",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    text=text,
    voice="Cherry",
    language_type="Chinese", # 建议与文本语种一致，以获得正确的发音和自然的语调。
    stream=False
)
audio_url = response.output.audio.url
save_path = "downloaded_audio.wav"  # 自定义保存路径

try:
    response = requests.get(audio_url)
    response.raise_for_status()  # 检查请求是否成功
    with open(save_path, 'wb') as f:
        f.write(response.content)
    print(f"音频文件已保存至：{save_path}")
except Exception as e:
    print(f"下载失败：{str(e)}")
    

实时播放
Qwen-TTS 模型可以流式地将音频数据以 Base64 格式进行输出，并在最后一个数据包中包含完整音频的 URL。

PythonJavacurl

 
#  DashScope SDK 版本不低于 1.24.6
# coding=utf-8
#
# Installation instructions for pyaudio:
# APPLE Mac OS X
#   brew install portaudio
#   pip install pyaudio
# Debian/Ubuntu
#   sudo apt-get install python-pyaudio python3-pyaudio
#   or
#   pip install pyaudio
# CentOS
#   sudo yum install -y portaudio portaudio-devel && pip install pyaudio
# Microsoft Windows
#   python -m pip install pyaudio

import os
import dashscope
import pyaudio
import time
import base64
import numpy as np

p = pyaudio.PyAudio()
# 创建音频流
stream = p.open(format=pyaudio.paInt16,
                channels=1,
                rate=24000,
                output=True)


text = "你好啊，我是通义千问"
response = dashscope.MultiModalConversation.call(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model="qwen3-tts-flash",
    text=text,
    voice="Cherry",
    language_type="Chinese",  # 建议与文本语种一致，以获得正确的发音和自然的语调。
    stream=True
)

for chunk in response:
    audio = chunk.output.audio
    if audio.data is not None:
        wav_bytes = base64.b64decode(audio.data)
        audio_np = np.frombuffer(wav_bytes, dtype=np.int16)
        # 直接播放音频数据
        stream.write(audio_np.tobytes())
    if chunk.output.finish_reason == "stop":
        print("finish at: {} ", chunk.output.audio.expires_at)
time.sleep(0.8)
# 清理资源
stream.stop_stream()
stream.close()
p.terminate()

API 参考
请参见语音合成（Qwen-TTS）。

支持的音色
不同模型支持的音色有所差异，使用时将请求参数voice设置为如下表格的voice参数列对应的值：

Qwen3-TTSQwen-TTS
音色名

voice参数

音色效果

描述

支持的语种

芊悦

Cherry

阳光积极、亲切自然小姐姐。

中文、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

晨煦

Ethan

标准普通话，带部分北方口音。阳光、温暖、活力、朝气。

中文、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

不吃鱼

Nofish

不会翘舌音的设计师。

中文、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

詹妮弗

Jennifer

品牌级、电影质感般美语女声。

中文、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

甜茶

Ryan

节奏拉满，戏感炸裂，真实与张力共舞。

中文、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

卡捷琳娜

Katerina

御姐音色，韵律回味十足。

中文、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

墨讲师

Elias

既保持学科严谨性，又通过叙事技巧将复杂知识转化为可消化的认知模块。

中文、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

上海-阿珍

Jada

风风火火的沪上阿姐。

中文（上海话）、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

北京-晓东

Dylan

北京胡同里长大的少年。

中文（北京话）、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

四川-晴儿

Sunny

甜到你心里的川妹子。

中文（四川话）、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

南京-老李

li

耐心的瑜伽老师

中文（南京话）、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

陕西-秦川

Marcus

面宽话短，心实声沉——老陕的味道。

中文（陕西话）、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

闽南-阿杰

Roy

诙谐直爽、市井活泼的台湾哥仔形象。

中文（闽南语）、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

天津-李彼得

Peter

天津相声，专业捧人。

中文（天津话）、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

粤语-阿强

Rocky

幽默风趣的阿强，在线陪聊。

中文（粤语）、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

粤语-阿清

Kiki

甜美的港妹闺蜜。

中文（粤语）、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语

四川-程川

Eric

一个跳脱市井的四川成都男子。

中文（四川话）、英语、法语、德语、俄语、意大利语、西班牙语、葡萄牙语、日语、韩语