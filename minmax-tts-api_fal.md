# MiniMax Speech-02 HD

> Generate speech from text prompts and different voices using the MiniMax Speech-02 HD model, which leverages advanced AI techniques to create high-quality text-to-speech.

## 音色列表：

https://platform.minimaxi.com/document/system_voice_id?key=68b40964a96516e26018eee2

## Overview

- **Endpoint**: `https://fal.run/fal-ai/minimax/speech-02-hd`
- **Model ID**: `fal-ai/minimax/speech-02-hd`
- **Category**: text-to-speech
- **Kind**: inference
**Tags**: speech



## API Information

This model can be used via our HTTP API or more conveniently via our client libraries.
See the input and output schema below, as well as the usage examples.


### Input Schema

The API accepts the following input parameters:


- **`text`** (`string`, _required_):
  Text to convert to speech (max 5000 characters, minimum 1 non-whitespace character)
  - Examples: "Hello world! This is a test of the text-to-speech system."

- **`voice_setting`** (`VoiceSetting`, _optional_):
  Voice configuration settings
  - Default: `{"speed":1,"vol":1,"voice_id":"Wise_Woman","pitch":0,"english_normalization":false}`

- **`audio_setting`** (`AudioSetting`, _optional_):
  Audio configuration settings

- **`language_boost`** (`LanguageBoostEnum`, _optional_):
  Enhance recognition of specified languages and dialects
  - Options: `"Chinese"`, `"Chinese,Yue"`, `"English"`, `"Arabic"`, `"Russian"`, `"Spanish"`, `"French"`, `"Portuguese"`, `"German"`, `"Turkish"`, `"Dutch"`, `"Ukrainian"`, `"Vietnamese"`, `"Indonesian"`, `"Japanese"`, `"Italian"`, `"Korean"`, `"Thai"`, `"Polish"`, `"Romanian"`, `"Greek"`, `"Czech"`, `"Finnish"`, `"Hindi"`, `"Bulgarian"`, `"Danish"`, `"Hebrew"`, `"Malay"`, `"Slovak"`, `"Swedish"`, `"Croatian"`, `"Hungarian"`, `"Norwegian"`, `"Slovenian"`, `"Catalan"`, `"Nynorsk"`, `"Afrikaans"`, `"auto"`

- **`output_format`** (`OutputFormatEnum`, _optional_):
  Format of the output content (non-streaming only) Default value: `"hex"`
  - Default: `"hex"`
  - Options: `"url"`, `"hex"`

- **`pronunciation_dict`** (`PronunciationDict`, _optional_):
  Custom pronunciation dictionary for text replacement



**Required Parameters Example**:

```json
{
  "text": "Hello world! This is a test of the text-to-speech system."
}
```

**Full Example**:

```json
{
  "text": "Hello world! This is a test of the text-to-speech system.",
  "voice_setting": {
    "speed": 1,
    "vol": 1,
    "voice_id": "Wise_Woman",
    "pitch": 0,
    "english_normalization": false
  },
  "output_format": "hex"
}
```


### Output Schema

The API returns the following output format:

- **`audio`** (`File`, _required_):
  The generated audio file
  - Examples: {"url":"https://fal.media/files/kangaroo/kojPUCNZ9iUGFGMR-xb7h_speech.mp3"}

- **`duration_ms`** (`integer`, _required_):
  Duration of the audio in milliseconds



**Example Response**:

```json
{
  "audio": {
    "url": "https://fal.media/files/kangaroo/kojPUCNZ9iUGFGMR-xb7h_speech.mp3"
  }
}
```


## Usage Examples

### cURL

```bash
curl --request POST \
  --url https://fal.run/fal-ai/minimax/speech-02-hd \
  --header "Authorization: Key $FAL_KEY" \
  --header "Content-Type: application/json" \
  --data '{
     "text": "Hello world! This is a test of the text-to-speech system."
   }'
```

### Python

Ensure you have the Python client installed:

```bash
pip install fal-client
```

Then use the API client to make requests:

```python
import fal_client

def on_queue_update(update):
    if isinstance(update, fal_client.InProgress):
        for log in update.logs:
           print(log["message"])

result = fal_client.subscribe(
    "fal-ai/minimax/speech-02-hd",
    arguments={
        "text": "Hello world! This is a test of the text-to-speech system."
    },
    with_logs=True,
    on_queue_update=on_queue_update,
)
print(result)
```

### JavaScript

Ensure you have the JavaScript client installed:

```bash
npm install --save @fal-ai/client
```

Then use the API client to make requests:

```javascript
import { fal } from "@fal-ai/client";

const result = await fal.subscribe("fal-ai/minimax/speech-02-hd", {
  input: {
    text: "Hello world! This is a test of the text-to-speech system."
  },
  logs: true,
  onQueueUpdate: (update) => {
    if (update.status === "IN_PROGRESS") {
      update.logs.map((log) => log.message).forEach(console.log);
    }
  },
});
console.log(result.data);
console.log(result.requestId);
```


## Additional Resources

### Documentation

- [Model Playground](https://fal.ai/models/fal-ai/minimax/speech-02-hd)
- [API Documentation](https://fal.ai/models/fal-ai/minimax/speech-02-hd/api)
- [OpenAPI Schema](https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=fal-ai/minimax/speech-02-hd)

### fal.ai Platform

- [Platform Documentation](https://docs.fal.ai)
- [Python Client](https://docs.fal.ai/clients/python)
- [JavaScript Client](https://docs.fal.ai/clients/javascript)