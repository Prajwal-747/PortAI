import os
import base64
import io
import time

import ctranslate2
import keyboard
import numpy as np
import pyautogui
import sounddevice as sd
import torch
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from openai import OpenAI
from ping3 import ping

load_dotenv()

# --- Global Settings ---
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

Answer the user's question using only information that is clearly visible
in the screenshot.

Do not guess, infer, or invent information that is not visible.

If the requested information is partially visible, clearly state what you
can determine and what cannot be determined.

If the screenshot is insufficient to answer the question, say so.

Be concise and directly answer the user's question.
"""

conversation_history = []


# --- Core Backend Functions ---

def check_internet():
    response = ping("8.8.8.8", timeout=2)
    return response is not None


def get_vram_gb():
    try:
        return torch.cuda.get_device_properties(0).total_memory / (1024**3)
    except Exception:
        return -1


def load_whisper_model():
    if torch.cuda.is_available():
        vram_gb = get_vram_gb()
        if 0 < vram_gb <= 3.0:
            model_name = "base"
        elif vram_gb > 3.0:
            model_name = "turbo"
        else:
            model_name = "base"
        try:
            supported_compute_types = ctranslate2.get_supported_compute_types("cuda")
            if "float16" in supported_compute_types:
                compute_type = "float16"
            elif "int8_float16" in supported_compute_types:
                compute_type = "int8_float16"
            else:
                compute_type = "float32"

            return WhisperModel(
                model_name, device="cuda", compute_type=compute_type
            )
        except Exception as e:
            print(f"CUDA initialization failed: {e}")
            print("Falling back to CPU.")
    return WhisperModel("base", device="cpu", compute_type="int8")


def record_audio_until_released():
    audio_chunks = []

    def audio_callback(indata, _frames, _time_info, status):
        if status:
            print(status)
        audio_chunks.append(indata.copy())

    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=CHANNELS, callback=audio_callback
    ):
        while keyboard.is_pressed("ctrl") and keyboard.is_pressed("alt"):
            time.sleep(0.02)

    return audio_chunks


def transcribe_audio(whisper_model, audio_chunks):
    if not audio_chunks:
        return None

    audio_samples = np.concatenate(audio_chunks, axis=0).flatten().astype(np.float32)

    if len(audio_samples) < SAMPLE_RATE * 0.5:
        return None

    segments, _ = whisper_model.transcribe(
        audio_samples, beam_size=5, language="en", vad_filter=True
    )
    transcribed_text = "".join([segment.text for segment in segments]).strip()

    if transcribed_text:
        return transcribed_text
    return None


def classify_query_type(prompt, conversation_history):
    history_transcribed_text = ""
    for message in conversation_history:
        history_transcribed_text += f"{message['role']}: {message['content']}\n"

    classifier_prompt = f"""
You are a routing classifier.

Your ONLY job is to classify the LATEST USER MESSAGE.

Return EXACTLY ONE WORD:

TEXT
or
VISION
or
CLEARCONTEXT

CONVERSATION HISTORY:
{history_transcribed_text}

LATEST USER MESSAGE:
{prompt}

CLASSIFICATION RULES:

TEXT:
- The latest message can be answered using transcribed_text.
- General knowledge questions are TEXT.
- Coding questions are TEXT.
- Conversational questions are TEXT.
- Follow-up questions are TEXT if their meaning can be understood from the conversation history.

VISION:
- The latest message requires seeing the user's screen, window, UI, image, or other visual information.
- The user explicitly asks about something visible on their screen.
- The answer cannot be determined from the conversation history and requires visual information.

CLEARCONTEXT:
- The latest message is a query about clearing the conversation context.
- the user asks to clear the conversation history or context
- the user may ask you to forget the previous messages
- the user may ask you to reset the conversation

IMPORTANT:
- Use the conversation history ONLY to understand references such as "it", "that", "this", or "they".
- NEVER answer the latest user message.
- NEVER explain your classification.
- NEVER provide reasoning.
- Output ONLY TEXT or VISION or CLEARCONTEXT.
"""

    response = client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=[{"role": "user", "content": classifier_prompt}],
    )

    answer = response.choices[0].message.content.strip().upper()
    print(f"RAW CLASSIFIER OUTPUT: {repr(answer)}")
    if answer not in {"TEXT", "VISION", "CLEARCONTEXT"}:
        return "UNKNOWN"

    return answer


def generate_text_response(prompt):
    global conversation_history
    conversation_history.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Answer the question in a concise and informative manner.",
            },
            *conversation_history,
        ],
    )
    answer = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": answer})
    return answer


def generate_vision_response(prompt):
    global conversation_history

    screenshot = pyautogui.screenshot()
    screenshot_buffer = io.BytesIO()
    screenshot.save(screenshot_buffer, format="PNG")
    screenshot_bytes = screenshot_buffer.getvalue()

    screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")
    ss_url = f"data:image/png;base64,{screenshot_base64}"

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": ss_url}},
                ],
            },
        ],
    )
    answer = response.choices[0].message.content

    conversation_history.append({"role": "user", "content": prompt})
    conversation_history.append({"role": "assistant", "content": answer})

    return answer, screenshot_bytes
