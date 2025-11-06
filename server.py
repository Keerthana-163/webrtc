import os
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import httpx

# ---------------------------
# Config
# ---------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in your environment.")

REALTIME_MODEL = os.getenv("REALTIME_MODEL", "gpt-4o-realtime-preview")
VOICE = os.getenv("VOICE", "alloy")

app = FastAPI(title="WebRTC Interview – Python Server")

# Serve ./static (index.html, client JS inlined)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    # Serve your main page
    return FileResponse("static/index.html")

@app.post("/session")
async def create_ephemeral_session(_: Request) -> JSONResponse:
    """
    Issues an OpenAI Realtime **ephemeral** key for the browser.
    The browser will use this to make a direct WebRTC connection to OpenAI.
    """
    url = "https://api.openai.com/v1/realtime/sessions"
    payload: Dict[str, Any] = {
        "model": REALTIME_MODEL,
        # Force English-only + TTS voice
        "voice": VOICE,
        "instructions": "You are a structured technical interviewer. Respond ONLY in English.",
        # Ensure audio+text output is available by default
        "modalities": ["audio", "text"],
        # Lock STT to English
        "input_audio_transcription": {"model": "whisper-1", "language": "en"},
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1"
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()

    # Return the whole session object (contains client_secret)
    return JSONResponse(data)
