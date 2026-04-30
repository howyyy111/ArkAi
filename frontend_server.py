import os
import sys
import uvicorn

DEFAULT_PORT = 4173
DEFAULT_HOST = "127.0.0.1"

def main() -> None:
    port = int(os.environ.get("PORT") or os.environ.get("ARKAIS_FRONTEND_PORT", str(DEFAULT_PORT)))
    host = os.environ.get("ARKAIS_FRONTEND_HOST", DEFAULT_HOST)
    
    print(f"Starting the modernized ARKAIS frontend on http://{host}:{port} via FastAPI", file=sys.stderr)
    uvicorn.run("ark_learning_agent.main:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()
