import asyncio
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
import logging
import json
import os
import posixpath
import re
import zoneinfo
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

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
from ark_learning_agent.learner_state import (
    build_or_update_roadmap,
    create_assessment,
    delete_all_learning_history,
    delete_learning_history_item,
    delete_roadmap,
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
from ark_learning_agent.web_session_store import (
    append_chat_message,
    delete_all_chat_sessions,
    delete_chat_session,
    get_chat_messages,
    get_or_create_browser_identity,
    get_or_create_chat_session,
    list_chat_sessions,
)
from ark_learning_agent.firestore_session_service import FirestoreSessionService

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
APP_NAME = "arkais-frontend"
LOGGER = logging.getLogger(__name__)
DEFAULT_PORT = 4173
DEFAULT_HOST = "127.0.0.1"
DEFAULT_AGENT_TIMEOUT_SECONDS = 90
DEFAULT_AGENT_APP_NAME = "agent"
CLIENT_COOKIE_NAME = "arkais_client_id"
SESSION_COOKIE_NAME = "arkais_session_id"
FIREBASE_SESSION_COOKIE_NAME = "arkais_firebase_session"
FIREBASE_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 5
AUTH_CALLBACK_CREDENTIAL_PATHS = (
    BASE_DIR / "auth_function" / "credentials.json",
    BASE_DIR / "ark_learning_agent" / "credentials.json",
)


def _persistent_session_backend_required() -> bool:
    if (os.environ.get("ARKAIS_ALLOW_IN_MEMORY_SESSIONS") or "").strip() == "1":
        return False
    return bool(os.environ.get("K_SERVICE"))


def _initialize_session_service():
    firestore_service = FirestoreSessionService()
    if firestore_service.is_available():
        return firestore_service
    return InMemorySessionService()


def _validate_session_backend_or_raise(session_backend) -> None:
    if _persistent_session_backend_required() and not (
        isinstance(session_backend, FirestoreSessionService)
        and session_backend.is_available()
    ):
        LOGGER.warning(
            "Persistent Firestore-backed sessions are unavailable in production; "
            "falling back to in-memory sessions for this frontend instance."
        )

session_service = _initialize_session_service()
_validate_session_backend_or_raise(session_service)
runner: Runner | None = None
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


def _remote_agent_timeout_seconds() -> float:
    return float(
        os.environ.get(
            "ARKAIS_AGENT_TIMEOUT_SECONDS",
            str(DEFAULT_AGENT_TIMEOUT_SECONDS),
        )
    )


def _get_runner() -> Runner:
    global runner
    if runner is None:
        from ark_learning_agent.agent import root_agent

        runner = Runner(
            app_name=APP_NAME,
            agent=root_agent,
            session_service=session_service,
        )
    return runner


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


def _production_https_redirect_uri_from_secrets(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return ""

    web = payload.get("web") or {}
    for uri in web.get("redirect_uris") or []:
        value = str(uri or "").strip()
        if value.startswith("https://"):
            return value
    return ""


def _resolved_auth_callback_url() -> str:
    for key in ("OAUTH_REDIRECT_URI", "AUTH_CALLBACK_URL"):
        value = (os.environ.get(key) or "").strip()
        if value:
            return value

    for path in AUTH_CALLBACK_CREDENTIAL_PATHS:
        value = _production_https_redirect_uri_from_secrets(path)
        if value:
            return value
    return ""


def _system_status() -> dict[str, Any]:
    firebase_web = _firebase_web_config()
    firebase_project = (
        os.environ.get("FIREBASE_PROJECT_ID")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or ""
    ).strip()
    oauth_ready = (BASE_DIR / "ark_learning_agent" / "credentials.json").is_file()
    auth_callback_url = _resolved_auth_callback_url()
    vertex_enabled = (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") or "").strip() == "1"
    cloud_run_ready = bool(os.environ.get("PORT") or os.environ.get("K_SERVICE"))
    firestore_mode = "sqlite_fallback" if (os.environ.get("ARKAIS_FORCE_SQLITE") or "").strip() == "1" else "firestore_preferred"
    session_backend = "firestore" if isinstance(session_service, FirestoreSessionService) and session_service.is_available() else "in_memory_fallback"
    persistent_sessions_required = _persistent_session_backend_required()
    return {
        "status": "success",
        "stack": {
            "frontend": "Cloud Run compatible Python server",
            "agent_runtime": "Google ADK",
            "database_mode": firestore_mode,
            "session_backend": session_backend,
            "model_routing": "Vertex AI Gemini" if vertex_enabled else "Gemini API or fallback",
        },
        "readiness": {
            "firebase_web_auth": bool(firebase_web),
            "firebase_project_configured": bool(firebase_project),
            "oauth_client_present": oauth_ready,
            "auth_callback_configured": bool(auth_callback_url),
            "vertex_ai_enabled": vertex_enabled,
            "cloud_run_runtime": cloud_run_ready,
            "persistent_sessions_required": persistent_sessions_required,
            "persistent_sessions_ready": session_backend == "firestore",
            "materials_library": True,
            "browser_voice_mode": True,
        },
        "metrics": app_metrics,
        "integrations": {
            "auth_callback_url": auth_callback_url,
        },
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


def _session_cookie_token(headers) -> str:
    cookie = SimpleCookie()
    raw = headers.get("Cookie")
    if raw:
        cookie.load(raw)
    morsel = cookie.get(FIREBASE_SESSION_COOKIE_NAME)
    if not morsel:
        return ""
    return str(morsel.value).strip()


def _verify_firebase_id_token_email(id_token: str) -> str:
    _firebase_admin_app()
    decoded = firebase_auth.verify_id_token(id_token)
    email = str(decoded.get("email", "")).strip()
    if not email:
        raise PermissionError("Firebase token did not include an email address.")
    return email


def _resolve_authenticated_user(payload: dict[str, Any], headers) -> tuple[str, str]:
    session_cookie = _session_cookie_token(headers)
    if session_cookie:
        try:
            _firebase_admin_app()
            decoded = firebase_auth.verify_session_cookie(session_cookie, check_revoked=True)
            email = str(decoded.get("email", "")).strip()
            if not email:
                raise PermissionError("Firebase session did not include an email address.")
            return email, session_cookie
        except Exception as exc:
            raise PermissionError(f"Invalid Firebase session cookie: {exc}") from exc

    id_token = str(payload.get("idToken", "")).strip() or _authorization_token(headers)
    if not id_token:
        return "", ""

    try:
        return _verify_firebase_id_token_email(id_token), id_token
    except Exception as exc:
        raise PermissionError(f"Invalid Firebase ID token: {exc}") from exc


def _display_name_for_user(user_id: str) -> str:
    normalized = str(user_id).strip()
    if normalized.startswith("guest:"):
        return f"Guest {normalized[-6:]}"
    return normalized


def _create_firebase_session_cookie(id_token: str) -> str:
    _firebase_admin_app()
    return firebase_auth.create_session_cookie(
        id_token,
        expires_in=timedelta(seconds=FIREBASE_SESSION_MAX_AGE_SECONDS),
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


def _is_google_doc_save_request(message: str) -> bool:
    text = str(message or "").strip().lower()
    if "save" not in text:
        return False
    return any(
        phrase in text
        for phrase in (
            "google doc",
            "google docs",
            "my docs",
            "docs",
            "doc",
            "document",
        )
    )


def _is_google_drive_save_request(message: str) -> bool:
    text = str(message or "").strip().lower()
    return "save" in text and ("google drive" in text or "drive" in text)


def _is_google_task_save_request(message: str) -> bool:
    text = str(message or "").strip().lower()
    return (
        ("save" in text or "add" in text or "create" in text)
        and any(phrase in text for phrase in ("google task", "google tasks", "task", "tasks", "todo", "to-do"))
    )


def _is_google_calendar_save_request(message: str) -> bool:
    text = str(message or "").strip().lower()
    return (
        ("save" in text or "add" in text or "create" in text or "schedule" in text or "put" in text or "sync" in text)
        and any(phrase in text for phrase in ("google calendar", "google calender", "calendar", "calender", "gcal", "event"))
    )


def _is_google_save_request(message: str) -> bool:
    return (
        _is_google_doc_save_request(message)
        or _is_google_drive_save_request(message)
        or _is_google_task_save_request(message)
        or _is_google_calendar_save_request(message)
    )


def _clean_google_save_text(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def _truncate_google_save_text(value: Any, limit: int) -> str:
    text = _clean_google_save_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _google_save_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    for message in messages:
        content = _clean_google_save_text(message.get("content", ""))
        if not content or _is_google_save_request(content):
            continue
        role = str(message.get("role", "")).strip().lower()
        author = "You" if role == "user" else "ArkAI"
        cleaned.append({"role": role, "author": author, "content": content})
    return cleaned


def _latest_google_save_content(cleaned_messages: list[dict[str, str]], role: str) -> str:
    role = role.lower()
    for message in reversed(cleaned_messages):
        if message.get("role") == role:
            return message.get("content", "")
    return ""


def _chat_doc_title(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if str(message.get("role", "")).lower() == "user":
            content = str(message.get("content", "")).strip()
            if content and not _is_google_save_request(content):
                cleaned = re.sub(r"\s+", " ", content)
                return f"ArkAI Tutor - {cleaned[:48]}"
    return "ArkAI Tutor Notes"


def _format_chat_messages_for_google_doc(messages: list[dict[str, Any]]) -> str:
    cleaned_messages = _google_save_messages(messages)
    lines = ["ArkAI Tutor Notes", ""]
    if not cleaned_messages:
        lines.append("No tutor content was available to save yet.")
        return "\n".join(lines).strip()

    prompt = _latest_google_save_content(cleaned_messages, "user")
    answer = _latest_google_save_content(cleaned_messages, "assistant") or _latest_google_save_content(
        cleaned_messages,
        "agent",
    )

    if prompt:
        lines.extend(["Prompt", prompt, ""])
    if answer:
        lines.extend(["Tutor response", answer, ""])

    earlier_messages = cleaned_messages[:-2] if len(cleaned_messages) > 2 else []
    if earlier_messages:
        lines.extend(["Earlier context"])
        for message in earlier_messages[-6:]:
            lines.append(f"{message['author']}: {_truncate_google_save_text(message['content'], 700)}")
        lines.append("")

    return "\n".join(lines).strip()


def _format_chat_messages_for_google_drive(messages: list[dict[str, Any]]) -> str:
    cleaned_messages = _google_save_messages(messages)
    lines = ["# ArkAI Tutor Notes", ""]
    if not cleaned_messages:
        lines.append("No tutor content was available to save yet.")
        return "\n".join(lines).strip()

    prompt = _latest_google_save_content(cleaned_messages, "user")
    answer = _latest_google_save_content(cleaned_messages, "assistant") or _latest_google_save_content(
        cleaned_messages,
        "agent",
    )
    if prompt:
        lines.extend(["## Prompt", prompt, ""])
    if answer:
        lines.extend(["## Tutor response", answer, ""])
    if len(cleaned_messages) > 2:
        lines.extend(["## Earlier context"])
        for message in cleaned_messages[:-2][-6:]:
            lines.append(f"- **{message['author']}**: {_truncate_google_save_text(message['content'], 500)}")
    return "\n".join(lines).strip()


def _format_chat_messages_for_google_task(messages: list[dict[str, Any]]) -> str:
    cleaned_messages = _google_save_messages(messages)
    if not cleaned_messages:
        return "Created from ArkAI Tutor."
    prompt = _latest_google_save_content(cleaned_messages, "user")
    answer = _latest_google_save_content(cleaned_messages, "assistant") or _latest_google_save_content(
        cleaned_messages,
        "agent",
    )
    parts = ["Created from ArkAI Tutor."]
    if prompt:
        parts.extend(["", "Prompt:", _truncate_google_save_text(prompt, 600)])
    if answer:
        parts.extend(["", "Tutor response:", _truncate_google_save_text(answer, 2400)])
    return "\n".join(parts).strip()


def _format_chat_messages_for_google_calendar(messages: list[dict[str, Any]]) -> str:
    cleaned_messages = _google_save_messages(messages)
    if not cleaned_messages:
        return "Created from ArkAI Tutor."
    prompt = _latest_google_save_content(cleaned_messages, "user")
    answer = _latest_google_save_content(cleaned_messages, "assistant") or _latest_google_save_content(
        cleaned_messages,
        "agent",
    )
    parts = ["ArkAI Tutor study session."]
    if prompt:
        parts.extend(["", "Focus:", _truncate_google_save_text(prompt, 350)])
    if answer:
        parts.extend(["", "Notes:", _truncate_google_save_text(answer, 1200)])
    return "\n".join(parts).strip()


def _get_tutor_chat_save_payload(user_id: str, session_id: str) -> dict[str, Any]:
    from ark_learning_agent.productivity_mcp_server import google_oauth_status

    oauth_status = google_oauth_status(user_id)
    if not oauth_status.get("connected"):
        return {
            "status": "auth_required",
            "message": "Google saves is not connected for this signed-in ArkAI account.",
        }

    history = get_chat_messages(user_id, session_id=session_id)
    if history.get("status") != "success":
        return {
            "status": "error",
            "message": history.get("message") or "Could not read the current Tutor chat.",
        }

    messages = history.get("messages") or []
    return {
        "status": "success",
        "messages": messages,
        "title": _chat_doc_title(messages),
        "note_text": _format_chat_messages_for_google_doc(messages),
        "drive_text": _format_chat_messages_for_google_drive(messages),
        "task_notes": _format_chat_messages_for_google_task(messages),
        "calendar_description": _format_chat_messages_for_google_calendar(messages),
    }


def _save_tutor_chat_to_google_doc(user_id: str, session_id: str) -> dict[str, Any]:
    from ark_learning_agent.productivity_mcp_server import save_google_doc_note

    payload = _get_tutor_chat_save_payload(user_id, session_id)
    if payload.get("status") != "success":
        return payload
    return save_google_doc_note(
        user_id=user_id,
        title=payload["title"],
        note_text=payload["note_text"],
    )


def _save_tutor_chat_to_google_drive(user_id: str, session_id: str) -> dict[str, Any]:
    from ark_learning_agent.productivity_mcp_server import save_text_file_to_drive

    payload = _get_tutor_chat_save_payload(user_id, session_id)
    if payload.get("status") != "success":
        return payload
    return save_text_file_to_drive(
        user_id=user_id,
        title=payload["title"],
        content=payload["drive_text"],
    )


def _save_tutor_chat_to_google_task(user_id: str, session_id: str) -> dict[str, Any]:
    from ark_learning_agent.productivity_mcp_server import create_study_task

    payload = _get_tutor_chat_save_payload(user_id, session_id)
    if payload.get("status") != "success":
        return payload
    return create_study_task(
        user_id=user_id,
        task_title=f"Review {payload['title']}",
        notes=payload["task_notes"],
    )


def _calendar_window_from_message(message: str, timezone_name: str = "") -> tuple[str, str] | None:
    start = _calendar_start_from_message(message, timezone_name)
    if not start:
        return None
    end = start + timedelta(minutes=30)
    return start.isoformat(), end.isoformat()


def _calendar_start_from_message(message: str, timezone_name: str = "") -> datetime | None:
    tz_name = timezone_name or "Asia/Bangkok"
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except zoneinfo.ZoneInfoNotFoundError:
        tz = zoneinfo.ZoneInfo("Asia/Bangkok")
    now = datetime.now(tz)
    text = str(message or "").strip().lower()
    date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if date_match:
        event_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
    elif "tomorrow" in text:
        event_date = (now + timedelta(days=1)).date()
    elif "today" in text:
        event_date = now.date()
    else:
        weekdays = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        weekday = next((day for name, day in weekdays.items() if name in text), None)
        if weekday is None:
            return None
        days_ahead = (weekday - now.weekday()) % 7
        if days_ahead == 0 or "next" in text:
            days_ahead = days_ahead or 7
        event_date = (now + timedelta(days=days_ahead)).date()

    time_match = re.search(r"(?<![-\d])(\d{1,2})(?::(\d{2}))?\s*(am|pm)?(?![-\d])", text)
    if not time_match:
        return None
    hour = int(time_match.group(1))
    minute = int(time_match.group(2) or 0)
    suffix = time_match.group(3)
    if suffix == "pm" and hour < 12:
        hour += 12
    if suffix == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None

    return datetime(event_date.year, event_date.month, event_date.day, hour, minute, tzinfo=tz)


def _requested_session_count(message: str, default: int) -> int:
    text = str(message or "").strip().lower()
    digit_match = re.search(r"\b(\d{1,2})\s+(?:study\s+)?sessions?\b", text)
    if digit_match:
        return max(1, min(default, int(digit_match.group(1))))
    words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    for word, count in words.items():
        if re.search(rf"\b{word}\s+(?:study\s+)?sessions?\b", text):
            return max(1, min(default, count))
    return default


def _is_roadmap_calendar_request(message: str) -> bool:
    text = str(message or "").strip().lower()
    return _is_google_calendar_save_request(text) and any(
        phrase in text
        for phrase in ("roadmap", "study session", "study sessions", "sessions", "session plan")
    )


def _save_tutor_chat_to_google_calendar(user_id: str, session_id: str, message: str, timezone_name: str) -> dict[str, Any]:
    from ark_learning_agent.productivity_mcp_server import create_calendar_event

    payload = _get_tutor_chat_save_payload(user_id, session_id)
    if payload.get("status") != "success":
        return payload
    window = _calendar_window_from_message(message, timezone_name)
    if not window:
        return {
            "status": "needs_time",
            "message": "Tell me a date and time, for example: save this to Google Calendar tomorrow at 9am.",
        }
    start_time, end_time = window
    return create_calendar_event(
        user_id=user_id,
        event_title=payload["title"],
        start_time_iso=start_time,
        end_time_iso=end_time,
        description=payload["calendar_description"],
    )


def _save_roadmap_sessions_to_google_calendar(user_id: str, message: str, timezone_name: str) -> dict[str, Any]:
    from ark_learning_agent.productivity_mcp_server import create_calendar_event, google_oauth_status

    oauth_status = google_oauth_status(user_id)
    if not oauth_status.get("connected"):
        return {
            "status": "auth_required",
            "message": "Google saves is not connected for this signed-in ArkAI account.",
        }
    start_at = _calendar_start_from_message(message, timezone_name)
    if not start_at:
        return {
            "status": "needs_time",
            "message": "Tell me when to start the calendar schedule, for example: add 5 study sessions to Google Calendar tomorrow at 9am.",
        }

    roadmap_result = get_roadmap(user_id)
    if roadmap_result.get("status") != "success":
        return {
            "status": "error",
            "message": roadmap_result.get("message") or "No active roadmap was found.",
        }

    sessions: list[dict[str, Any]] = []
    for phase in roadmap_result.get("roadmap", {}).get("phases", []):
        for session in phase.get("sessions", []):
            if session.get("status") == "completed":
                continue
            sessions.append(
                {
                    "phase_title": str(phase.get("title") or "").strip(),
                    "phase_goal": str(phase.get("goal") or "").strip(),
                    "title": str(session.get("title") or "Study session").strip(),
                    "focus": str(session.get("focus") or "").strip(),
                    "duration_minutes": int(session.get("duration_minutes") or 30),
                }
            )
    if not sessions:
        return {"status": "error", "message": "No upcoming roadmap sessions were found."}

    count = _requested_session_count(message, len(sessions))
    created = []
    for index, session in enumerate(sessions[:count]):
        start = start_at + timedelta(days=index)
        duration = max(15, min(240, int(session.get("duration_minutes") or 30)))
        end = start + timedelta(minutes=duration)
        description_parts = [
            f"Focus: {session['focus']}" if session.get("focus") else "",
            f"Phase: {session['phase_title']}" if session.get("phase_title") else "",
            session.get("phase_goal") or "",
            "Created from ArkAI Tutor.",
        ]
        result = create_calendar_event(
            user_id=user_id,
            event_title=f"Study: {session['title']}",
            start_time_iso=start.isoformat(),
            end_time_iso=end.isoformat(),
            description="\n".join(part for part in description_parts if part),
        )
        if result.get("status") != "success":
            return result
        created.append(session["title"])

    return {
        "status": "success",
        "message": f"Added {len(created)} roadmap session(s) to Google Calendar.",
        "created_sessions": created,
    }


def _build_agent_message(
    user_id: str,
    message: str,
    user_timezone: str = "",
    selected_material_ids: list[str] | None = None,
) -> str:
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
    if str(user_id).startswith("guest:"):
        identity_instruction = (
            "The active ARKAI browser session is a guest session with app user_id: "
            f"{user_id}\n"
            "For ARKAI learning-state tools, use this exact app user_id. For Google Docs, "
            "Google Calendar, or Google Tasks tools, use the Gmail/user_id the user provided "
            "for Google authorization if it appears in the conversation. If they have not "
            "provided one, use this app user_id so the OAuth callback saves credentials to "
            "the same guest session. Do not call a guest user_id a Gmail address.\n"
        )
    else:
        identity_instruction = (
            "The active signed-in user for this session is identified by this email address: "
            f"{user_id}\n"
            "For any Google Docs, Google Calendar, or Google Tasks action, use this exact "
            "email address as user_id. Do not ask again for Gmail unless the user explicitly "
            "wants to change accounts.\n"
        )

    return (
        identity_instruction
        +
        f"{timezone_info}\n"
        f"{learner_state_block}\n"
        f"{material_context_block}\n"
        f"User message:\n{message}"
    )


async def _run_agent(
    user_id: str,
    session_id: str,
    message: str,
    user_timezone: str = "",
    selected_material_ids: list[str] | None = None,
) -> str:
    active_runner = _get_runner()
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
    effective_message = _build_agent_message(
        user_id=user_id,
        message=message,
        user_timezone=user_timezone,
        selected_material_ids=selected_material_ids,
    )
    async for event in active_runner.run_async(
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


def _parse_adk_sse_payload(raw_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    data_lines: list[str] = []

    def flush_event() -> None:
        nonlocal data_lines
        if not data_lines:
            return
        payload = "\n".join(data_lines).strip()
        data_lines = []
        if not payload or payload == "[DONE]":
            return
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return
        if isinstance(parsed, list):
            events.extend(item for item in parsed if isinstance(item, dict))
        elif isinstance(parsed, dict):
            events.append(parsed)

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            flush_event()
            continue
        if stripped.startswith("data:"):
            data_lines.append(stripped[5:].lstrip())

    flush_event()
    return events


def _extract_adk_events_from_response(response: requests.Response) -> list[dict[str, Any]]:
    try:
        parsed = response.json()
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            return [parsed]
    except json.JSONDecodeError:
        pass

    events = _parse_adk_sse_payload(response.text)
    if events:
        return events

    raise RuntimeError(
        "Remote agent returned a non-JSON response."
    )


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
    timeout_seconds = _remote_agent_timeout_seconds()

    session_state: dict[str, Any] = {}
    if user_timezone:
        session_state["user_timezone"] = user_timezone
    if selected_material_ids:
        session_state["selected_material_ids"] = selected_material_ids

    session_response = requests.get(session_url, headers=headers, timeout=timeout_seconds)
    if session_response.status_code == HTTPStatus.NOT_FOUND:
        create_response = requests.post(
            session_url,
            headers=headers,
            json=session_state or None,
            timeout=timeout_seconds,
        )
        create_response.raise_for_status()
    elif session_response.ok and session_state:
        patch_response = requests.patch(
            session_url,
            headers=headers,
            json={"stateDelta": session_state},
            timeout=timeout_seconds,
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
                "parts": [
                    {
                        "text": _build_agent_message(
                            user_id=user_id,
                            message=message,
                            user_timezone=user_timezone,
                            selected_material_ids=selected_material_ids,
                        )
                    }
                ],
            },
            "streaming": False,
        },
        timeout=timeout_seconds,
    )
    run_response.raise_for_status()

    events = _extract_adk_events_from_response(run_response)

    reply = _extract_reply_from_adk_events(events)
    if not reply:
        raise RuntimeError("Remote agent returned no reply text.")
    return reply


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class ArkAisHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._pending_cookies: list[str] = []
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def _cookies(self) -> SimpleCookie:
        cookie = SimpleCookie()
        raw = self.headers.get("Cookie")
        if raw:
            cookie.load(raw)
        return cookie

    def _cookie_value(self, name: str) -> str:
        morsel = self._cookies().get(name)
        if not morsel:
            return ""
        return str(morsel.value).strip()

    def _request_is_secure(self) -> bool:
        forwarded_proto = str(self.headers.get("X-Forwarded-Proto", "")).strip().lower()
        return forwarded_proto == "https"

    def _queue_cookie(
        self,
        name: str,
        value: str,
        *,
        max_age: int = 60 * 60 * 24 * 365,
        http_only: bool = True,
    ) -> None:
        parts = [f"{name}={value}", "Path=/", f"Max-Age={max_age}", "SameSite=Lax"]
        if http_only:
            parts.append("HttpOnly")
        if self._request_is_secure():
            parts.append("Secure")
        self._pending_cookies.append("; ".join(parts))

    def _clear_cookie(self, name: str, *, http_only: bool = True) -> None:
        self._queue_cookie(name, "", max_age=0, http_only=http_only)

    def _resolve_request_context(
        self,
        payload: dict[str, Any] | None = None,
        *,
        reset_identity: bool = False,
        reset_session: bool = False,
        requested_session_id: str = "",
        ignore_auth: bool = False,
    ) -> dict[str, Any]:
        payload = payload or {}
        if ignore_auth:
            authenticated_user_id = ""
        else:
            authenticated_user_id, _ = _resolve_authenticated_user(payload, self.headers)
        identity = get_or_create_browser_identity(
            client_id=self._cookie_value(CLIENT_COOKIE_NAME),
            authenticated_user_id=authenticated_user_id,
            reset_identity=reset_identity,
        )
        session = get_or_create_chat_session(
            client_id=str(identity["client_id"]),
            user_id=str(identity["user_id"]),
            session_id=requested_session_id or self._cookie_value(SESSION_COOKIE_NAME),
            reset_session=reset_session,
        )

        self._queue_cookie(CLIENT_COOKIE_NAME, str(identity["client_id"]))
        self._queue_cookie(SESSION_COOKIE_NAME, str(session["session_id"]))

        user_id = str(identity["user_id"])
        return {
            "user_id": user_id,
            "session_id": str(session["session_id"]),
            "is_anonymous": user_id.startswith("guest:"),
            "display_name": _display_name_for_user(user_id),
        }

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
        elif self.path.startswith("/api/session"):
            try:
                context = self._resolve_request_context()
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(
                HTTPStatus.OK,
                {
                    "status": "success",
                    "userId": context["user_id"],
                    "sessionId": context["session_id"],
                    "displayName": context["display_name"],
                    "isAnonymous": context["is_anonymous"],
                },
            )
            return
        elif self.path == "/api/system-status":
            self._write_json(HTTPStatus.OK, _system_status())
            return
        elif self.path.startswith("/api/demo-kit"):
            try:
                context = self._resolve_request_context()
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, get_demo_kit(context["user_id"]))
            return
        elif self.path.startswith("/api/learner-state"):
            try:
                context = self._resolve_request_context()
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, get_learner_state(context["user_id"]))
            return
        elif self.path.startswith("/api/mastery"):
            try:
                context = self._resolve_request_context()
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, get_mastery_snapshot(context["user_id"]))
            return
        elif self.path.startswith("/api/roadmap"):
            try:
                context = self._resolve_request_context()
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            result = get_roadmap(context["user_id"])
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.NOT_FOUND
            self._write_json(status, result)
            return
        elif self.path.startswith("/api/materials"):
            try:
                context = self._resolve_request_context()
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, list_learning_materials(context["user_id"]))
            return
        elif self.path.startswith("/api/chat/sessions"):
            try:
                context = self._resolve_request_context()
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            result = list_chat_sessions(context["user_id"], limit=30)
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return
        elif self.path.startswith("/api/chat/messages"):
            try:
                context = self._resolve_request_context()
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            from urllib.parse import parse_qs, urlparse

            query = parse_qs(urlparse(self.path).query)
            session_id = str((query.get("sessionId") or [""])[0]).strip()
            result = get_chat_messages(context["user_id"], session_id=session_id)
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.NOT_FOUND
            self._write_json(status, result)
            return
        elif self.path.startswith("/api/intervention"):
            try:
                context = self._resolve_request_context()
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, get_intervention_plan(context["user_id"]))
            return
        elif self.path.startswith("/api/evaluation"):
            try:
                context = self._resolve_request_context()
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            self._write_json(HTTPStatus.OK, get_evaluation_snapshot(context["user_id"]))
            return
        elif self.path.startswith("/api/google/status"):
            try:
                context = self._resolve_request_context()
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return
            if context["is_anonymous"]:
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "status": "success",
                        "connected": False,
                        "message": "Sign in with Google to connect saves.",
                    },
                )
                return
            from ark_learning_agent.productivity_mcp_server import google_oauth_status

            self._write_json(HTTPStatus.OK, google_oauth_status(context["user_id"]))
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path not in {
            "/api/session",
            "/api/auth/session",
            "/api/auth/logout",
            "/api/google/connect",
            "/api/chat",
            "/api/chat/delete",
            "/api/chat/delete-all",
            "/api/diagnostic/start",
            "/api/diagnostic/submit",
            "/api/roadmap/generate",
            "/api/roadmap/delete",
            "/api/roadmap/session/update",
            "/api/roadmap/save-google-tasks",
            "/api/roadmap/session/save-calendar",
            "/api/materials/upload",
            "/api/materials/tutor",
            "/api/materials/mock-test",
            "/api/materials/delete",
            "/api/materials/delete-all",
            "/api/history/delete",
            "/api/history/delete-all",
            "/api/report/generate",
            "/api/report/save-google-doc",
            "/api/assessment/save-google-doc",
        }:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 20 * 1024 * 1024:  # 20 MB limit
                self._write_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "Payload exceeds the 20MB limit."})
                return
            raw_body = self.rfile.read(length)
            payload = json.loads(raw_body or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body."})
            return

        if self.path == "/api/auth/session":
            id_token = str(payload.get("idToken", "")).strip() or _authorization_token(self.headers)
            if not id_token:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Missing Firebase ID token."})
                return
            try:
                user_id = _verify_firebase_id_token_email(id_token)
                session_cookie = _create_firebase_session_cookie(id_token)
                self._queue_cookie(
                    FIREBASE_SESSION_COOKIE_NAME,
                    session_cookie,
                    max_age=FIREBASE_SESSION_MAX_AGE_SECONDS,
                    http_only=True,
                )
                context = self._resolve_request_context(payload)
            except PermissionError as exc:
                self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
                return

            self._write_json(
                HTTPStatus.OK,
                {
                    "status": "success",
                    "userId": user_id,
                    "sessionId": context["session_id"],
                    "displayName": context["display_name"],
                    "isAnonymous": False,
                },
            )
            return

        if self.path == "/api/auth/logout":
            self._clear_cookie(FIREBASE_SESSION_COOKIE_NAME)
            context = self._resolve_request_context(
                payload,
                reset_identity=bool(payload.get("resetIdentity", True)),
                reset_session=bool(payload.get("resetSession", True)),
                ignore_auth=True,
            )
            self._write_json(
                HTTPStatus.OK,
                {
                    "status": "success",
                    "userId": context["user_id"],
                    "sessionId": context["session_id"],
                    "displayName": context["display_name"],
                    "isAnonymous": context["is_anonymous"],
                },
            )
            return

        if self.path == "/api/google/connect":
            context = self._resolve_request_context(payload)
            if context["is_anonymous"]:
                self._write_json(
                    HTTPStatus.UNAUTHORIZED,
                    {
                        "status": "error",
                        "message": "Sign in with Google before connecting Docs, Calendar, and Tasks.",
                    },
                )
                return
            from ark_learning_agent.productivity_mcp_server import get_google_authorization_url

            result = get_google_authorization_url(context["user_id"])
            status = HTTPStatus.OK if result.get("status") in {"success", "auth_required"} else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        try:
            context = self._resolve_request_context(
                payload,
                reset_identity=bool(payload.get("resetIdentity", False)),
                reset_session=bool(payload.get("resetSession", False)),
                requested_session_id=str(payload.get("sessionId", "")).strip(),
            )
        except PermissionError as exc:
            self._write_json(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})
            return
        user_id = context["user_id"]

        if self.path == "/api/session":
            self._write_json(
                HTTPStatus.OK,
                {
                    "status": "success",
                    "userId": context["user_id"],
                    "sessionId": context["session_id"],
                    "displayName": context["display_name"],
                    "isAnonymous": context["is_anonymous"],
                },
            )
            return

        if self.path == "/api/chat/delete":
            result = delete_chat_session(
                user_id=user_id,
                session_id=str(payload.get("targetSessionId", "")).strip(),
            )
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/chat/delete-all":
            result = delete_all_chat_sessions(user_id=user_id)
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
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

        if self.path == "/api/roadmap/delete":
            result = delete_roadmap(user_id=user_id)
            status = HTTPStatus.OK if result.get("status") == "success" else HTTPStatus.NOT_FOUND
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

        if self.path == "/api/roadmap/save-google-tasks":
            from ark_learning_agent.productivity_mcp_server import create_roadmap_tasks, google_oauth_status

            oauth_status = google_oauth_status(user_id)
            if not oauth_status.get("connected"):
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "status": "auth_required",
                        "message": "Connect Google saves from the account menu before saving roadmap tasks.",
                    },
                )
                return

            result = create_roadmap_tasks(user_id=user_id, include_due_dates=False)
            if result.get("status") in {"success", "auth_required"}:
                status = HTTPStatus.OK
            else:
                status = HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        if self.path == "/api/roadmap/session/save-calendar":
            from ark_learning_agent.productivity_mcp_server import create_calendar_event, google_oauth_status

            oauth_status = google_oauth_status(user_id)
            if not oauth_status.get("connected"):
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "status": "auth_required",
                        "message": "Connect Google saves from the account menu before saving calendar events.",
                    },
                )
                return

            title = str(payload.get("title", "")).strip() or "Roadmap study session"
            focus = str(payload.get("focus", "")).strip()
            phase_title = str(payload.get("phaseTitle", "")).strip()
            phase_goal = str(payload.get("phaseGoal", "")).strip()
            start_time = str(payload.get("startTime", "")).strip()
            end_time = str(payload.get("endTime", "")).strip()
            if not start_time or not end_time:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Choose a start time first."})
                return

            description_parts = [
                f"Focus: {focus}" if focus else "",
                f"Phase: {phase_title}" if phase_title else "",
                phase_goal,
                "Created from ArkAI roadmap.",
            ]
            result = create_calendar_event(
                user_id=user_id,
                event_title=f"Study: {title}",
                start_time_iso=start_time,
                end_time_iso=end_time,
                description="\n".join(part for part in description_parts if part),
            )
            if result.get("status") in {"success", "auth_required"}:
                status = HTTPStatus.OK
            else:
                status = HTTPStatus.BAD_REQUEST
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
            from ark_learning_agent.productivity_mcp_server import google_oauth_status, save_weekly_report_doc

            oauth_status = google_oauth_status(user_id)
            if not oauth_status.get("connected"):
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "status": "auth_required",
                        "message": "Connect Google saves from the account menu before saving reports.",
                    },
                )
                return

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

        if self.path == "/api/assessment/save-google-doc":
            from ark_learning_agent.productivity_mcp_server import google_oauth_status, save_assessment_doc

            oauth_status = google_oauth_status(user_id)
            if not oauth_status.get("connected"):
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "status": "auth_required",
                        "message": "Connect Google saves from the account menu before saving assessments.",
                    },
                )
                return

            result = save_assessment_doc(
                user_id=user_id,
                assessment_id=str(payload.get("assessmentId", "")).strip(),
                title=str(payload.get("title", "")).strip(),
            )
            if result.get("status") in {"success", "auth_required"}:
                status = HTTPStatus.OK
            else:
                status = HTTPStatus.BAD_REQUEST
            self._write_json(status, result)
            return

        message = str(payload.get("message", "")).strip()
        session_id = context["session_id"]
        user_timezone = str(payload.get("timezone", "")).strip()
        selected_material_ids = [
            str(item) for item in (payload.get("selectedMaterialIds") or []) if str(item).strip()
        ]
        input_mode = str(payload.get("inputMode", "")).strip().lower()

        if not message:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Missing message."})
            return

        try:
            app_metrics["chat_requests"] += 1
            append_chat_message(
                user_id=user_id,
                session_id=session_id,
                role="user",
                author="user",
                content=message,
                metadata={
                    "timezone": user_timezone,
                    "selected_material_ids": selected_material_ids,
                    "input_mode": input_mode,
                },
            )
            if _is_google_save_request(message):
                try:
                    if _is_google_drive_save_request(message):
                        save_result = _save_tutor_chat_to_google_drive(user_id=user_id, session_id=session_id)
                    elif _is_google_task_save_request(message):
                        save_result = _save_tutor_chat_to_google_task(user_id=user_id, session_id=session_id)
                    elif _is_google_calendar_save_request(message):
                        if _is_roadmap_calendar_request(message):
                            save_result = _save_roadmap_sessions_to_google_calendar(
                                user_id=user_id,
                                message=message,
                                timezone_name=user_timezone,
                            )
                        else:
                            save_result = _save_tutor_chat_to_google_calendar(
                                user_id=user_id,
                                session_id=session_id,
                                message=message,
                                timezone_name=user_timezone,
                            )
                    else:
                        save_result = _save_tutor_chat_to_google_doc(user_id=user_id, session_id=session_id)
                except Exception as exc:
                    LOGGER.exception("Tutor Google save failed for user %s", user_id)
                    save_result = {
                        "status": "error",
                        "message": str(exc) or exc.__class__.__name__,
                    }

                if save_result.get("status") == "success":
                    reply = save_result.get("message") or "Saved this Tutor chat."
                    doc_id = str(save_result.get("doc_id") or "").strip()
                    web_view_link = str(save_result.get("web_view_link") or "").strip()
                    if doc_id:
                        reply = f"{reply}\n\nDocument: https://docs.google.com/document/d/{doc_id}/edit"
                    elif web_view_link:
                        reply = f"{reply}\n\nFile: {web_view_link}"
                elif save_result.get("status") == "needs_time":
                    reply = save_result.get("message") or "Tell me a date and time for the calendar event."
                elif save_result.get("status") == "auth_required":
                    reply = (
                        "Google saves is still not connected for the signed-in ArkAI account I can verify. "
                        "Open the account menu, connect Google saves again, then retry."
                    )
                else:
                    reply = f"I could not complete that Google save: {save_result.get('message') or 'unknown error'}"
                append_chat_message(
                    user_id=user_id,
                    session_id=session_id,
                    role="assistant",
                    author="ARKAI",
                    content=reply,
                )
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "reply": reply,
                        "session": {
                            "userId": context["user_id"],
                            "sessionId": context["session_id"],
                            "displayName": context["display_name"],
                            "isAnonymous": context["is_anonymous"],
                        },
                    },
                )
                return
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
                        timeout=_remote_agent_timeout_seconds(),
                    )
                )
            append_chat_message(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                author="ARKAI",
                content=reply,
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

        self._write_json(
            HTTPStatus.OK,
            {
                "reply": reply,
                "session": {
                    "userId": context["user_id"],
                    "sessionId": context["session_id"],
                    "displayName": context["display_name"],
                    "isAnonymous": context["is_anonymous"],
                },
            },
        )

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
        for cookie in self._pending_cookies:
            self.send_header("Set-Cookie", cookie)
        self._pending_cookies.clear()
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
