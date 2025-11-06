# server.py
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY")

# Use a model your account actually has access to.
# Common options: "gpt-4o-realtime-preview"
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
    return {"ok": bool(OPENAI_API_KEY), "model": REALTIME_MODEL, "voice": VOICE}

@app.post("/session")
async def create_ephemeral_session():
    """
    Create an ephemeral Realtime session for the browser.
    IMPORTANT: Only send fields the endpoint supports.
    """
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "OpenAI-Beta": "realtime=v1",
    }
    payload = {
        "model": REALTIME_MODEL,
        # optional:
        "voice": VOICE,
        # "expires_in": 60,  # optional TTL seconds
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                json=payload,
                headers=headers,
            )
    except httpx.RequestError as e:
        return JSONResponse({"error": "request_error", "detail": str(e)}, status_code=502)

    # Pass through upstream response if non-2xx so the UI shows the true error.
    if r.status_code // 100 != 2:
        ctype = r.headers.get("content-type", "")
        if "application/json" in ctype:
            return JSONResponse(r.json(), status_code=r.status_code)
        return PlainTextResponse(r.text, status_code=r.status_code)

    return JSONResponse(r.json())
