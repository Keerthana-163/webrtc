import os
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import httpx

# ===== Config =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY env var")

REALTIME_MODEL = os.getenv("REALTIME_MODEL", "gpt-4o-realtime-preview")
VOICE = os.getenv("VOICE", "alloy")

# Defaults mirroring your CLI
DEFAULT_ROLE = os.getenv("ROLE", "PCB Designer")
DEFAULT_OPENING = os.getenv(
    "OPENING_QUESTION",
    "Tell me about your experience with Ki Cad or Altium for PCB design."
)

app = FastAPI(title="WebRTC Interview (Python)")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/session")
async def create_ephemeral_session(req: Request) -> JSONResponse:
    """
    Issues an ephemeral key for browser Realtime.
    You can pass role/opening from the client if you want (optional).
    """
    try:
        body = await req.json()
    except Exception:
        body = {}

    role = (body.get("role") or DEFAULT_ROLE).strip()
    opening = (body.get("opening") or DEFAULT_OPENING).strip()

    # The 'instructions' make the model follow your CLI logic:
    # - Speak only the question (audio)
    # - Put analysis in TEXT channel as JSON tagged block
    # - Keep questions <20 words
    instructions = f"""
You are a structured technical interviewer for the role: {role}.
Rules:
1) Speak ONLY the question aloud (audio). Do not speak analysis.
2) Keep each question < 20 words, voice-friendly.
3) After speaking, send a TEXT-only block with EXACT JSON tagged as:
[ANALYSIS_JSON] {{"analysis":"...", "reasoning_focus":"...", "quality_signals":"..."}}
No extra commentary outside JSON. Keep analysis concise (1–2 sentences).
4) Continue as a conversational interviewer: listen to candidate's voice, then ask the next question.
"""

    payload: Dict[str, Any] = {
        "model": REALTIME_MODEL,
        "voice": VOICE,
        "instructions": instructions,
        "modalities": ["audio", "text"],
        "input_audio_transcription": {"model": "whisper-1", "language": "en"},
    }

    # Provide an initial user message so the first spoken output is your opening
    # The Realtime session remembers history after connection.
    payload["conversation"] = {
        "messages": [
            {"role": "user", "content": f"Start the interview. First question: {opening}"}
        ]
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post("https://api.openai.com/v1/realtime/sessions",
                              json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
    return JSONResponse(data)
