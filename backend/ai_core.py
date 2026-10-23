import base64
import io
import os
import time
import ctranslate2
import numpy as np
import pyautogui
import sounddevice as sd
import torch
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from openai import OpenAI
from ping3 import ping

load_dotenv()

SAMPLE_RATE = 16000
CHANNELS = 1

client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.getenv("NEBIUS_API_KEY"),
)

CLASSIFIER_MODEL = "MiniMaxAI/MiniMax-M3"
TEXT_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
VISION_MODEL = "zai-org/GLM-5.3-Flash"

VISION_SYSTEM_PROMPT = """
You are PortAI, a desktop AI assistant that analyzes screenshots.
Answer the user's question using only information that is clearly visible in the screenshot.
Do not guess, infer, or invent information that is not visible.
Be concise and directly answer the user's question.
"""

conversation_history = []

def check_internet():
    try:
        response = ping("8.8.8.8", timeout=2)
        return response is not None
    except Exception:
        return False

def get_vram_gb():
    try:
        return torch.cuda.get_device_properties(0).total_memory / (1024**3)
    except Exception:
        return -1

def load_whisper_model():
    if torch.cuda.is_available():
        vram_gb = get_vram_gb()
        model_name = "turbo" if vram_gb > 3.0 else "base"
        try:
            supported = ctranslate2.get_supported_compute_types("cuda")
            compute_type = "float16" if "float16" in supported else "int8_float16"
            return WhisperModel(model_name, device="cuda", compute_type=compute_type)
        except Exception:
            pass
    return WhisperModel("base", device="cpu", compute_type="int8")

def record_audio_until_released(keyboard_module):
    audio_chunks = []
    def audio_callback(indata, _frames, _time_info, status):
        if status:
            print(status)
        audio_chunks.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=audio_callback):
        while keyboard_module.is_pressed("ctrl") and keyboard_module.is_pressed("alt"):
            time.sleep(0.02)
    return audio_chunks

def transcribe_audio(whisper_model, audio_chunks):
    if not audio_chunks:
        return None
    audio_samples = np.concatenate(audio_chunks, axis=0).flatten().astype(np.float32)
    if len(audio_samples) < SAMPLE_RATE * 0.5:
        return None
    segments, _ = whisper_model.transcribe(audio_samples, beam_size=5, language="en", vad_filter=True)
    text = "".join([s.text for s in segments]).strip()
    return text if text else None

def classify_query_type(prompt, history):
    history_text = "".join([f"{m['role']}: {m['content']}\n" for m in history])
    classifier_prompt = f"""
You are a routing classifier. Return EXACTLY ONE WORD: TEXT, VISION, or CLEARCONTEXT.
HISTORY:
{history_text}
LATEST:
{prompt}
"""
    try:
        response = client.chat.completions.create(
            model=CLASSIFIER_MODEL,
            messages=[{"role": "user", "content": classifier_prompt}],
        )
        answer = response.choices[0].message.content.strip().upper()
        if answer in {"TEXT", "VISION", "CLEARCONTEXT"}:
            return answer
    except Exception:
        pass
    return "TEXT"

def generate_text_response(prompt):
    global conversation_history
    conversation_history.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": "Answer concisely."},
            *conversation_history,
        ],
    )
    answer = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": answer})
    return answer

def generate_vision_response(prompt):
    global conversation_history
    screenshot = pyautogui.screenshot()
    buf = io.BytesIO()
    screenshot.save(buf, format="PNG")
    ss_bytes = buf.getvalue()
    ss_base64 = base64.b64encode(ss_bytes).decode("utf-8")
    ss_url = f"data:image/png;base64,{ss_base64}"

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": ss_url}}]},
        ],
    )
    answer = response.choices[0].message.content
    conversation_history.append({"role": "user", "content": prompt})
    conversation_history.append({"role": "assistant", "content": answer})
    return answer, ss_bytes