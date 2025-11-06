import os
import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# --------- CONFIG ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in Render dashboard.")

MODEL_REALTIME = os.getenv("MODEL_REALTIME", "gpt-4o-realtime-preview")
VOICE = os.getenv("VOICE", "alloy")

app = FastAPI()

# serve / and /static/*
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/session")
async def create_realtime_session():
    """
    Create a short-lived client token for the browser to connect to OpenAI Realtime via WebRTC.
    """
    url = "https://api.openai.com/v1/realtime/sessions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_REALTIME,
        "voice": VOICE,
        "instructions": (
            "You are a structured technical interviewer for the role 'PCB Designer'. "
            "Speak naturally in short sentences. Ask exactly one concise question at a time "
            "(under 20 words). Keep the conversation voice-friendly and interactive. "
            "If the user is silent for a while, gently prompt them."
        ),
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    # The JSON includes client_secret.value (ephemeral token) and model name
    return JSONResponse(data)
