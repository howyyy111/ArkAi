import asyncio
import json
import os
import posixpath
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import firebase_admin
from firebase_admin import auth as firebase_auth

from ark_learning_agent.demo_assets import get_demo_kit
from ark_learning_agent.materials import (
    build_material_context,
    create_mock_test_from_materials,
    delete_all_learning_materials,
    delete_learning_material,
    list_learning_materials,
    save_learning_material,
    tutor_from_materials,
)
from ark_learning_agent.agent import root_agent
from ark_learning_agent.learner_state import (
    build_or_update_roadmap,
    create_assessment,
    delete_all_learning_history,
    delete_learning_history_item,
    describe_learner_state,
    generate_weekly_report,
    get_evaluation_snapshot,
    get_intervention_plan,
    get_learner_state,
    get_mastery_snapshot,
    get_roadmap,
    submit_assessment,
    update_roadmap_session,
)
from ark_learning_agent.productivity_mcp_server import save_weekly_report_doc

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
APP_NAME = "arkais-frontend"
DEFAULT_PORT = 4173
DEFAULT_HOST = "127.0.0.1"
DEFAULT_AGENT_TIMEOUT_SECONDS = 90
DEFAULT_AGENT_APP_NAME = "ark_learning_agent"

session_service = InMemorySessionService()
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)
app_metrics = {
    "chat_requests": 0,
    "diagnostics_started": 0,
    "diagnostics_submitted": 0,
    "roadmaps_generated": 0,
    "roadmap_updates": 0,
    "materials_uploaded": 0,
    "materials_tutored": 0,
    "reports_generated": 0,
    "reports_saved_to_docs": 0,
}


def _remote_agent_base_url() -> str:
    return (os.environ.get("ARKAIS_AGENT_API_URL") or "").strip().rstrip("/")


def _remote_agent_app_name() -> str:
    return (os.environ.get("ARKAIS_AGENT_APP_NAME") or DEFAULT_AGENT_APP_NAME).strip()


def _firebase_web_config() -> dict[str, str] | None:
    config = {
        "apiKey": os.environ.get("FIREBASE_API_KEY", "").strip(),
        "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN", "").strip(),
        "projectId": os.environ.get("FIREBASE_PROJECT_ID", "").strip(),
        "appId": os.environ.get("FIREBASE_APP_ID", "").strip(),
    }
    optional = {
        "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", "").strip(),
        "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET", "").strip(),
    }
    config.update({key: value for key, value in optional.items() if value})
    return config if all(config.values()) else None


def _system_status() -> dict[str, Any]:
    firebase_web = _firebase_web_config()
    firebase_project = (
        os.environ.get("FIREBASE_PROJECT_ID")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or ""
    ).strip()
    oauth_ready = (BASE_DIR / "ark_learning_agent" / "credentials.json").is_file()
    auth_callback_url = (os.environ.get("AUTH_CALLBACK_URL") or "").strip()
    vertex_enabled = (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") or "").strip() == "1"
    cloud_run_ready = bool(os.environ.get("PORT") or os.environ.get("K_SERVICE"))
    firestore_mode = "sqlite_fallback" if (os.environ.get("ARKAIS_FORCE_SQLITE") or "").strip() == "1" else "firestore_preferred"
    return {
        "status": "success",
        "stack": {
            "frontend": "Cloud Run compatible Python server",
            "agent_runtime": "Google ADK",
            "database_mode": firestore_mode,
            "model_routing": "Vertex AI Gemini" if vertex_enabled else "Gemini API or fallback",
        },
        "readiness": {
            "firebase_web_auth": bool(firebase_web),
            "firebase_project_configured": bool(firebase_project),
            "oauth_client_present": oauth_ready,
            "auth_callback_configured": bool(auth_callback_url),
            "vertex_ai_enabled": vertex_enabled,
            "cloud_run_runtime": cloud_run_ready,
            "materials_library": True,
            "browser_voice_mode": True,
        },
        "metrics": app_metrics,
        "recommended_next_steps": [
            "Enable Vertex AI and Firestore for the strongest Google-native architecture story.",
            "Deploy the frontend server to Cloud Run and keep Firebase Auth web config in env vars.",
            "Use Google Docs and Google Tasks workflows in the demo to show end-to-end value.",
        ],
    }


def _firebase_admin_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        project_id = (
            os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCLOUD_PROJECT")
            or os.environ.get("FIREBASE_PROJECT_ID")
            or ""
        ).strip()
        if project_id:
            return firebase_admin.initialize_app(options={"projectId": project_id})
        return firebase_admin.initialize_app()


def _authorization_token(headers) -> str:
    auth_header = str(headers.get("Authorization", "")).strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return ""


def _resolve_user(payload: dict[str, Any], headers) -> tuple[str, str]:
    id_token = str(payload.get("idToken", "")).strip() or _authorization_token(headers)
    fallback_user_id = str(payload.get("userId", "frontend-user")).strip() or "frontend-user"

    if not id_token:
        return fallback_user_id, ""

    try:
        _firebase_admin_app()
        decoded = firebase_auth.verify_id_token(id_token)
        email = str(decoded.get("email", "")).strip()
        return email or fallback_user_id, id_token
    except Exception as exc:
        raise PermissionError(f"Invalid Firebase ID token: {exc}") from exc


def _extract_text(content: types.Content | None) -> str:
    if not content or not content.parts:
        return ""

    chunks: list[str] = []
    for part in content.parts:
        text = getattr(part, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


async def _run_agent(
    user_id: str,
    session_id: str,
    message: str,
    user_timezone: str = "",
    selected_material_ids: list[str] | None = None,
) -> str:
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
    timezone_info = f"\nUser's local timezone: {user_timezone}\n" if user_timezone else ""
    learner_context = describe_learner_state(user_id)
    learner_state_block = (
        f"\nKnown learner state:\n{learner_context}\n" if learner_context else ""
    )
    material_context = build_material_context(
        user_id=user_id,
        query=message,
        material_ids=selected_material_ids or [],
        limit=3,
    )
    material_context_block = (
        f"\nRelevant learner materials:\n{material_context.get('context_text', '')}\n"
        if material_context.get("context_text")
        else ""
    )
    effective_message = (
        "The active signed-in user for this session is identified by this Gmail address: "
        f"{user_id}\n"
        "For any Google Docs, Google Calendar, or Google Tasks action, use this exact Gmail "
        "address as user_id. Do not ask again for Gmail unless the user explicitly wants to "
        "change accounts.\n"
        f"{timezone_info}\n"
        f"{learner_state_block}\n"
        f"{material_context_block}\n"
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


def _extract_reply_from_adk_events(events: list[dict[str, Any]]) -> str:
    reply_chunks: list[str] = []

    for event in events:
        if str(event.get("author", "")).strip().lower() == "user":
            continue
        content = event.get("content") or {}
        for part in content.get("parts") or []:
            text = str(part.get("text", "")).strip()
            if text:
                reply_chunks.append(text)

    return "\n".join(reply_chunks).strip()


def _run_agent_remote(
    user_id: str,
    session_id: str,
    message: str,
    user_timezone: str = "",
    selected_material_ids: list[str] | None = None,
) -> str:
    base_url = _remote_agent_base_url()
    if not base_url:
        raise RuntimeError("Remote agent URL is not configured.")

    app_name = _remote_agent_app_name()
    headers = {"Content-Type": "application/json"}
    session_url = f"{base_url}/apps/{app_name}/users/{user_id}/sessions/{session_id}"
    run_url = f"{base_url}/run_sse"

    session_state: dict[str, Any] = {}
    if user_timezone:
        session_state["user_timezone"] = user_timezone
    if selected_material_ids:
        session_state["selected_material_ids"] = selected_material_ids

    session_response = requests.get(session_url, headers=headers, timeout=15)
    if session_response.status_code == HTTPStatus.NOT_FOUND:
        create_response = requests.post(
            session_url,
            headers=headers,
            json=session_state or None,
            timeout=15,
        )
        create_response.raise_for_status()
    elif session_response.ok and session_state:
        patch_response = requests.patch(
            session_url,
            headers=headers,
            json={"stateDelta": session_state},
            timeout=15,
        )
        patch_response.raise_for_status()
    else:
        session_response.raise_for_status()

    run_response = requests.post(
        run_url,
        headers=headers,
        json={
            "appName": app_name,
            "userId": user_id,
            "sessionId": session_id,
            "newMessage": {
                "role": "user",
                "parts": [{"text": message}],
            },
            "streaming": False,
        },
        timeout=float(
            os.environ.get(
                "ARKAIS_AGENT_TIMEOUT_SECONDS",
                str(DEFAULT_AGENT_TIMEOUT_SECONDS),
            )
        ),
    )
    run_response.raise_for_status()

    events = run_response.json()
    if not isinstance(events, list):
        raise RuntimeError("Remote agent returned an unexpected response shape.")

    reply = _extract_reply_from_adk_events(events)
    if not reply:
        raise RuntimeError("Remote agent returned no reply text.")
    return reply


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
        elif self.path == "/api/config":
            self._write_json(
                HTTPStatus.OK,
                {
                    "firebase": _firebase_web_config(),
                    "authMode": "firebase" if _firebase_web_config() else "email_fallback",
                },
            )
            return
        elif self.path == "/api/system-status":
            self._write_json(HTTPStatus.OK, _system_status())
            return
        elif self.path.startswith("/api/demo-kit"):
            user_id = ""
            try:
                parsed = urlparse(self.path)
                user_id = parse_qs(parsed.query).get("userId", [""])[0]
                user_id, _ = _resolve_user({"userId": user_id}, self.headers)
            except PermissionError:
                user_id = parse_qs(urlparse(self.path).query).get("userId", ["frontend-user"])[0] or "frontend-user"
            self._write_json(HTTPStatus.OK, get_demo_kit(user_id))
            return
        elif self.path.startswith("/api/learner-state"):
            user_id = ""
            try:
                parsed = urlparse(self.path)
                user_id = parse_qs(parsed.query).get("userId", [""])[0]
                user_id, _ = _resolve_user({"userId": user_id}, self.headers)
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, get_learner_state(user_id))
            return
        elif self.path.startswith("/api/mastery"):
            user_id = ""
            try:
                parsed = urlparse(self.path)
                user_id = parse_qs(parsed.query).get("userId", [""])[0]
                user_id, _ = _resolve_user({"userId": user_id}, self.headers)
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, get_mastery_snapshot(user_id))
            return
        elif self.path.startswith("/api/roadmap"):
            user_id = ""
            try:
                parsed = urlparse(self.path)
                user_id = parse_qs(parsed.query).get("userId", [""])[0]
                user_id, _ = _resolve_user({"userId": user_id}, self.headers)
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            result = get_roadmap(user_id)
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.NOT_FOUND
            self._write_json(status, result)
            return
        elif self.path.startswith("/api/materials"):
            user_id = ""
            try:
                parsed = urlparse(self.path)
                user_id = parse_qs(parsed.query).get("userId", [""])[0]
                user_id, _ = _resolve_user({"userId": user_id}, self.headers)
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, list_learning_materials(user_id))
            return
        elif self.path.startswith("/api/intervention"):
            user_id = ""
            try:
                parsed = urlparse(self.path)
                user_id = parse_qs(parsed.query).get("userId", [""])[0]
                user_id, _ = _resolve_user({"userId": user_id}, self.headers)
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, get_intervention_plan(user_id))
            return
        elif self.path.startswith("/api/evaluation"):
            user_id = ""
            try:
                parsed = urlparse(self.path)
                user_id = parse_qs(parsed.query).get("userId", [""])[0]
                user_id, _ = _resolve_user({"userId": user_id}, self.headers)
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, get_evaluation_snapshot(user_id))
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path not in {
            "/api/chat",
            "/api/diagnostic/start",
            "/api/diagnostic/submit",
            "/api/roadmap/generate",
            "/api/roadmap/session/update",
            "/api/materials/upload",
            "/api/materials/tutor",
            "/api/materials/mock-test",
            "/api/materials/delete",
            "/api/materials/delete-all",
            "/api/history/delete",
            "/api/history/delete-all",
            "/api/report/generate",
            "/api/report/save-google-doc",
        }:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            payload = json.loads(raw_body or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body."})
            return

        try:
            user_id, _ = _resolve_user(payload, self.headers)
        except PermissionError as exc:
            self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            return

        if self.path == "/api/diagnostic/start":
            app_metrics["diagnostics_started"] += 1
            result = create_assessment(
                user_id=user_id,
                topic=str(payload.get("topic", "")).strip(),
                assessment_type=str(payload.get("assessmentType", "diagnostic")).strip() or "diagnostic",
                level=str(payload.get("level", "beginner")).strip() or "beginner",
                goal=str(payload.get("goal", "")).strip(),
                available_time=payload.get("availableTime"),
                learning_style=str(payload.get("learningStyle", "balanced")).strip() or "balanced",
                question_count=payload.get("questionCount", 5),
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/diagnostic/submit":
            app_metrics["diagnostics_submitted"] += 1
            result = submit_assessment(
                user_id=user_id,
                assessment_id=str(payload.get("assessmentId", "")).strip(),
                answers=payload.get("answers") or {},
                confidence_by_question=payload.get("confidenceByQuestion") or {},
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/roadmap/generate":
            app_metrics["roadmaps_generated"] += 1
            result = build_or_update_roadmap(
                user_id=user_id,
                topic=str(payload.get("topic", "")).strip(),
                goal=str(payload.get("goal", "")).strip(),
                level=str(payload.get("level", "")).strip(),
                available_time=payload.get("availableTime"),
                deadline_days=payload.get("deadlineDays", 14),
                force_rebuild=bool(payload.get("forceRebuild", False)),
                revision_reason=str(payload.get("revisionReason", "")).strip(),
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/roadmap/session/update":
            app_metrics["roadmap_updates"] += 1
            result = update_roadmap_session(
                user_id=user_id,
                phase_id=str(payload.get("phaseId", "")).strip(),
                session_id=str(payload.get("sessionId", "")).strip(),
                status=str(payload.get("status", "")).strip(),
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/materials/upload":
            app_metrics["materials_uploaded"] += 1
            result = save_learning_material(
                user_id=user_id,
                name=str(payload.get("name", "")).strip(),
                mime_type=str(payload.get("mimeType", "")).strip(),
                data_base64=str(payload.get("dataBase64", "")).strip(),
                pasted_text=str(payload.get("pastedText", "")).strip(),
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/materials/tutor":
            app_metrics["materials_tutored"] += 1
            result = tutor_from_materials(
                user_id=user_id,
                query=str(payload.get("query", "")).strip(),
                material_ids=[str(item) for item in (payload.get("materialIds") or []) if str(item).strip()],
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/materials/mock-test":
            result = create_mock_test_from_materials(
                user_id=user_id,
                material_ids=[str(item) for item in (payload.get("materialIds") or []) if str(item).strip()],
                topic=str(payload.get("topic", "")).strip(),
                level=str(payload.get("level", "beginner")).strip() or "beginner",
                goal=str(payload.get("goal", "")).strip(),
                question_count=payload.get("questionCount", 5),
                structure=str(payload.get("structure", "")).strip(),
                sample_style=str(payload.get("sampleStyle", "")).strip(),
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/materials/delete":
            result = delete_learning_material(
                user_id=user_id,
                material_id=str(payload.get("materialId", "")).strip(),
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/materials/delete-all":
            result = delete_all_learning_materials(user_id=user_id)
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/history/delete":
            result = delete_learning_history_item(
                user_id=user_id,
                record_id=str(payload.get("recordId", "")).strip(),
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/history/delete-all":
            result = delete_all_learning_history(user_id=user_id)
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/report/generate":
            app_metrics["reports_generated"] += 1
            result = generate_weekly_report(user_id)
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/report/save-google-doc":
            app_metrics["reports_saved_to_docs"] += 1
            result = save_weekly_report_doc(
                user_id=user_id,
                title=str(payload.get("title", "")).strip(),
            )
            if result.get("status") in {"success", "auth_required"}:
                status = HTTPStatus.OK
            else:
                status = HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        message = str(payload.get("message", "")).strip()
        session_id = str(payload.get("sessionId", "")).strip()
        user_timezone = str(payload.get("timezone", "")).strip()
        selected_material_ids = [
            str(item) for item in (payload.get("selectedMaterialIds") or []) if str(item).strip()
        ]
        input_mode = str(payload.get("inputMode", "")).strip().lower()

        if not message:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Missing message."})
            return
        if not session_id:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Missing sessionId."})
            return

        try:
            app_metrics["chat_requests"] += 1
            if _remote_agent_base_url():
                reply = _run_agent_remote(
                    user_id=user_id,
                    session_id=session_id,
                    message=message,
                    user_timezone=user_timezone,
                    selected_material_ids=selected_material_ids,
                )
            else:
                reply = asyncio.run(
                    asyncio.wait_for(
                        _run_agent(
                            user_id=user_id,
                            session_id=session_id,
                            message=message,
                            user_timezone=user_timezone,
                            selected_material_ids=selected_material_ids,
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

        if input_mode == "voice":
            try:
                from ark_learning_agent.learner_state import save_learning_progress

                save_learning_progress(
                    user_id=user_id,
                    topic="voice_tutor",
                    activity_type="voice_session",
                    notes=message[:500],
                    score=None,
                )
            except Exception:
                pass

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
