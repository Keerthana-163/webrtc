import os
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import httpx

# ===== Config =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY env var")

# If your account doesn’t have access to the Realtime preview you picked,
# you’ll get a 404/403 from OpenAI. Try another, e.g. "gpt-4o-realtime-preview".
REALTIME_MODEL = os.getenv("REALTIME_MODEL", "gpt-4o-realtime-preview")
VOICE = os.getenv("VOICE", "alloy")

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

@app.get("/health")
async def health():
    ok = bool(OPENAI_API_KEY)
    return {"ok": ok, "model": REALTIME_MODEL, "voice": VOICE}

@app.post("/session")
async def create_ephemeral_session(req: Request):
    """
    Issues an ephemeral key for browser Realtime.
    Returns upstream errors verbatim so the client can display them.
    """
    try:
        body = await req.json()
    except Exception:
        body = {}

    role = (body.get("role") or DEFAULT_ROLE).strip()
    opening = (body.get("opening") or DEFAULT_OPENING).strip()

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
        "conversation": {
            "messages": [
                {"role": "user", "content": f"Start the interview. First question: {opening}"}
            ]
        },
        # Optionally tighten TTL:
        # "expires_in": 60,
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                json=payload,
                headers=headers,
            )
    except httpx.RequestError as e:
        # Network/SSL/DNS errors
        return JSONResponse(
            {"error": "request_error", "detail": str(e)},
            status_code=502,
        )

    # Pass through OpenAI’s exact response if it’s not 2xx
    if resp.status_code // 100 != 2:
        # Try JSON; fall back to text
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return JSONResponse(resp.json(), status_code=resp.status_code)
        else:
            return PlainTextResponse(resp.text, status_code=resp.status_code)

    return JSONResponse(resp.json())
