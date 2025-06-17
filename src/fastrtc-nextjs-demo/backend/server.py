import fastapi
from fastrtc import ReplyOnPause, Stream, AlgoOptions, SileroVadOptions
from fastrtc.utils import audio_to_bytes, audio_to_float32
from openai import OpenAI
import logging
import time
from fastapi.middleware.cors import CORSMiddleware
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import numpy as np

ELEVENLABS_API_KEY = "ELEVENLABS_API_KEY"  # Replace with your ElevenLabs API key

sys_prompt = """
You are a helpful assistant. You are witty, engaging and fun. You love being interactive with the user. 
You also can add minimalistic utterances like 'uh-huh' or 'mm-hmm' to the conversation to make it more natural. However, only vocalization are allowed, no actions or other non-vocal sounds.
Begin a conversation with a self-deprecating joke like 'I'm not sure if I'm ready for this...' or 'I bet you already regret clicking that button...'
"""

messages = [{"role": "system", "content": sys_prompt}]

openai_client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama',  # required, but unused
)

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

logging.basicConfig(level=logging.INFO)

def echo(audio):
    stt_time = time.time()
    logging.info("Performing STT")
    transcription = elevenlabs_client.speech_to_text.convert(
        file=audio_to_bytes(audio),
        model_id="scribe_v1",
        tag_audio_events=False,
        language_code="eng",
        diarize=False,
    )
    prompt = transcription.text
    if prompt == "":
        logging.info("STT returned empty string")
        return
    logging.info(f"STT response: {prompt}")
    messages.append({"role": "user", "content": prompt})
    logging.info(f"STT took {time.time() - stt_time} seconds")

    llm_time = time.time()

    def text_stream():
        response = openai_client.chat.completions.create(
            model="qwen3:4b", messages=messages, max_tokens=200, stream=True
        )
        sentence = ""
        for chunk in response:
            if chunk.choices[0].finish_reason == "stop":
                break
            if chunk.choices[0].delta.content:
                sentence += chunk.choices[0].delta.content
                if '.' in sentence:
                    yield sentence
                    sentence = ""
        if sentence:
            yield sentence

    full_response = ""
    for sentence in text_stream():
        full_response += sentence
        audio_stream = elevenlabs_client.text_to_speech.stream(
            text=sentence,
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            model_id="eleven_multilingual_v2",
            output_format="pcm_24000",
            voice_settings=VoiceSettings(
                similarity_boost=0.9, stability=0.6, style=0.4, speed=1
            ),
        )
        for audio_chunk in audio_stream:
            audio_array = audio_to_float32(np.frombuffer(audio_chunk, dtype=np.int16))
            yield (24000, audio_array)

    messages.append({"role": "assistant", "content": full_response})
    logging.info(f"LLM response: {full_response}")
    logging.info(f"LLM took {time.time() - llm_time} seconds")

stream = Stream(
    ReplyOnPause(
        echo,
        algo_options=AlgoOptions(
            audio_chunk_duration=0.5,
            started_talking_threshold=0.1,
            speech_threshold=0.03,
        ),
        model_options=SileroVadOptions(
            threshold=0.75,
            min_speech_duration_ms=250,
            min_silence_duration_ms=1500,
            speech_pad_ms=400,
            max_speech_duration_s=15,
        ),
    ),
    modality="audio",
    mode="send-receive",
)

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stream.mount(app)

@app.get("/reset")
async def reset():
    global messages
    logging.info("Resetting chat")
    messages = [{"role": "system", "content": sys_prompt}]
    return {"status": "success"}