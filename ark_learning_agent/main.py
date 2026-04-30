import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from google.adk.cli import fast_api as adk_fast_api
from google.adk.sessions import InMemorySessionService

try:
    from .firestore_session_service import FirestoreSessionService
except ImportError:
    from firestore_session_service import FirestoreSessionService

from .frontend_api import api_router

def _running_on_cloud_run() -> bool:
    return bool(os.environ.get("K_SERVICE"))

AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = Path(AGENTS_DIR).parent
FRONTEND_DIR = BASE_DIR / "frontend"

ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("ARKAIS_AGENT_ALLOW_ORIGINS", "*").split(",")
    if origin.strip()
]
SERVE_WEB_INTERFACE = False
APP_HOST = os.environ.get("ARKAIS_AGENT_HOST", "0.0.0.0")
APP_PORT = int(os.environ.get("PORT", os.environ.get("ARKAIS_AGENT_PORT", "8000")))

def _create_session_service():
    if _running_on_cloud_run():
        firestore_session_service = FirestoreSessionService()
        if firestore_session_service.is_available():
            return firestore_session_service
    return InMemorySessionService()

def _build_app() -> FastAPI:
    agent_loader = adk_fast_api.AgentLoader(AGENTS_DIR)
    adk_fast_api.load_services_module(AGENTS_DIR)
    memory_service = adk_fast_api.create_memory_service_from_options(
        base_dir=AGENTS_DIR,
        memory_service_uri=None,
    )
    artifact_service = adk_fast_api.create_artifact_service_from_options(
        base_dir=AGENTS_DIR,
        artifact_service_uri=None,
        strict_uri=True,
        use_local_storage=True,
    )
    
    session_service = _create_session_service()
    
    adk_web_server = adk_fast_api.AdkWebServer(
        agent_loader=agent_loader,
        session_service=session_service,
        memory_service=memory_service,
        artifact_service=artifact_service,
        credential_service=adk_fast_api.InMemoryCredentialService(),
        eval_sets_manager=adk_fast_api.LocalEvalSetsManager(agents_dir=AGENTS_DIR),
        eval_set_results_manager=adk_fast_api.LocalEvalSetResultsManager(agents_dir=AGENTS_DIR),
        agents_dir=AGENTS_DIR,
    )

    web_assets_dir = None

    fastapi_app = adk_web_server.get_fast_api_app(
        allow_origins=ALLOW_ORIGINS,
        web_assets_dir=web_assets_dir,
    )
    
    # Expose session_service to our router
    fastapi_app.state.session_service = session_service

    fastapi_app.include_router(api_router)
    
    @fastapi_app.get("/")
    async def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
        
    fastapi_app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
    
    return fastapi_app

app: FastAPI = _build_app()

if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)
