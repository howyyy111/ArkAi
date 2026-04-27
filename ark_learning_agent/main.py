import os

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_SERVICE_URI = os.environ.get("ARKAIS_AGENT_SESSION_SERVICE_URI", "memory://")
ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("ARKAIS_AGENT_ALLOW_ORIGINS", "*").split(",")
    if origin.strip()
]
SERVE_WEB_INTERFACE = (
    os.environ.get("ARKAIS_AGENT_WITH_UI", "true").strip().lower() == "true"
)
APP_HOST = os.environ.get("ARKAIS_AGENT_HOST", "0.0.0.0")
APP_PORT = int(os.environ.get("PORT", os.environ.get("ARKAIS_AGENT_PORT", "8080")))

app: FastAPI = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=ALLOW_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)


if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
