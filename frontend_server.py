import asyncio
import json
import os
import posixpath
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from ark_learning_agent.agent import root_agent

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
APP_NAME = "arkais-frontend"
DEFAULT_PORT = 4173
DEFAULT_HOST = "127.0.0.1"
DEFAULT_AGENT_TIMEOUT_SECONDS = 90

session_service = InMemorySessionService()
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)


def _extract_text(content: types.Content | None) -> str:
    if not content or not content.parts:
        return ""

    chunks: list[str] = []
    for part in content.parts:
        text = getattr(part, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


async def _run_agent(*, user_id: str, session_id: str, message: str) -> str:
    if not session_service.get_session_sync(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    ):
        session_service.create_session_sync(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

    final_reply = ""
    effective_message = (
        "The active signed-in user for this session is identified by this Gmail address: "
        f"{user_id}\n"
        "For any Google Docs, Google Calendar, or Google Tasks action, use this exact Gmail "
        "address as user_id. Do not ask again for Gmail unless the user explicitly wants to "
        "change accounts.\n\n"
        f"User message:\n{message}"
    )
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(
            role="user",
            parts=[types.Part.from_text(text=effective_message)],
        ),
    ):
        if event.partial:
            continue
        text = _extract_text(event.content)
        if event.author != "user" and text:
            final_reply = text

    return final_reply or "The agent did not return any text."


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class ArkAisHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self.path = "/index.html"
        elif self.path == "/api/health":
            self._write_json(HTTPStatus.OK, {"status": "ok"})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            payload = json.loads(raw_body or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body."})
            return

        message = str(payload.get("message", "")).strip()
        session_id = str(payload.get("sessionId", "")).strip()
        user_id = str(payload.get("userId", "frontend-user")).strip() or "frontend-user"

        if not message:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Missing message."})
            return
        if not session_id:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Missing sessionId."})
            return

        try:
            reply = asyncio.run(
                asyncio.wait_for(
                    _run_agent(
                        user_id=user_id,
                        session_id=session_id,
                        message=message,
                    ),
                    timeout=float(
                        os.environ.get(
                            "ARKAIS_AGENT_TIMEOUT_SECONDS",
                            str(DEFAULT_AGENT_TIMEOUT_SECONDS),
                        )
                    ),
                )
            )
        except TimeoutError:
            self._write_json(
                HTTPStatus.GATEWAY_TIMEOUT,
                {"error": "Agent request timed out."},
            )
            return
        except Exception as exc:
            self._write_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Agent request failed: {exc}"},
            )
            return

        self._write_json(HTTPStatus.OK, {"reply": reply})

    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0].split("#", 1)[0]
        normalized = posixpath.normpath(path)
        parts = [part for part in normalized.split("/") if part]
        resolved = FRONTEND_DIR
        for part in parts:
            resolved = resolved / part
        return str(resolved)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    port = int(os.environ.get("PORT") or os.environ.get("ARKAIS_FRONTEND_PORT", str(DEFAULT_PORT)))
    host = os.environ.get("ARKAIS_FRONTEND_HOST", DEFAULT_HOST)
    server = ReusableThreadingHTTPServer((host, port), ArkAisHandler)
    print(f"ARKAIS frontend listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
