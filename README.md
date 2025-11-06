# GyanNidhi – WebRTC AI Interview (Render-ready)

This app serves a static page and a `/session` endpoint that mints **ephemeral tokens** for the browser to connect to **OpenAI Realtime** via **WebRTC**. The model speaks and listens in real time; no server-side media pipeline required.

## Quick start (local)

```bash
python -m venv .venv
. .venv/Scripts/activate   # Windows PowerShell
pip install -r requirements.txt
setx OPENAI_API_KEY "sk-proj-..."   # or use a .env loader if you prefer
uvicorn server:app --host 0.0.0.0 --port 8000
