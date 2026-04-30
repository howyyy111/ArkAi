import asyncio
from datetime import datetime, timedelta
import logging
import json
import os
import posixpath
import re
import zoneinfo
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse

import requests
from google.adk.runners import Runner
from google.genai import types
import firebase_admin
from firebase_admin import auth as firebase_auth

from .models import *
from .demo_assets import get_demo_kit
from .materials import (
    build_material_context,
    create_mock_test_from_materials,
    delete_all_learning_materials,
    delete_learning_material,
    _decode_base64,
    _extract_text_from_payload,
    list_learning_materials,
    save_learning_material,
    tutor_from_materials,
)
from .learner_state import (
    build_or_update_roadmap,
    create_assessment,
    delete_all_learning_history,
    delete_learning_history_item,
    delete_roadmap,
    delete_all_saved_roadmaps,
    delete_saved_roadmap,
    describe_learner_state,
    generate_weekly_report,
    get_evaluation_snapshot,
    get_intervention_plan,
    get_learner_state,
    get_mastery_snapshot,
    get_roadmap,
    list_roadmaps,
    submit_assessment,
    update_saved_roadmap_session,
    update_roadmap_session,
)
from .web_session_store import (
    append_chat_message,
    delete_all_chat_sessions,
    delete_chat_session,
    get_chat_messages,
    get_or_create_browser_identity,
    get_or_create_chat_session,
    list_chat_sessions,
)


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
APP_NAME = "arkais-frontend"
LOGGER = logging.getLogger(__name__)
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

runner: Runner | None = None

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
        from .agent import root_agent
        from .main import app as main_app
        session_service = main_app.state.session_service

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

def _system_status(request: Request) -> dict[str, Any]:
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
    
    main_app = request.app
    session_service = getattr(main_app.state, "session_service", None)
    try:
        from .firestore_session_service import FirestoreSessionService
        is_firestore = isinstance(session_service, FirestoreSessionService) and session_service.is_available()
    except ImportError:
        is_firestore = False
    
    session_backend = "firestore" if is_firestore else "in_memory_fallback"
    
    def _persistent_session_backend_required() -> bool:
        if (os.environ.get("ARKAIS_ALLOW_IN_MEMORY_SESSIONS") or "").strip() == "1":
            return False
        return bool(os.environ.get("K_SERVICE"))

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

def _email_fallback_auth_enabled() -> bool:
    return (
        (os.environ.get("ARKAIS_ALLOW_EMAIL_FALLBACK_AUTH") or "").strip() == "1"
        or _firebase_web_config() is None
    )

def _fallback_user_id_from_request(payload: dict[str, Any], headers) -> str:
    if not _email_fallback_auth_enabled():
        return ""

    raw_user_id = (
        str(payload.get("userId", "")).strip()
        or str(payload.get("username", "")).strip()
        or str(headers.get("X-Arkais-User", "")).strip()
    )
    normalized = raw_user_id.lower()[:120]
    if not normalized or normalized.startswith("guest:"):
        return ""
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
        return ""
    return normalized

def _session_cookie_token(cookies) -> str:
    return cookies.get(FIREBASE_SESSION_COOKIE_NAME, "").strip()

def _verify_firebase_id_token_email(id_token: str) -> str:
    _firebase_admin_app()
    decoded = firebase_auth.verify_id_token(id_token)
    email = str(decoded.get("email", "")).strip()
    if not email:
        raise PermissionError("Firebase token did not include an email address.")
    return email

def _resolve_authenticated_user(payload: dict[str, Any], request: Request) -> tuple[str, str]:
    session_cookie = _session_cookie_token(request.cookies)
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

    id_token = str(payload.get("idToken", "")).strip() or _authorization_token(request.headers)
    if not id_token:
        fallback_user_id = _fallback_user_id_from_request(payload, request.headers)
        return fallback_user_id, "email_fallback" if fallback_user_id else ""

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
        if not content:
            continue
        role = str(message.get("role", "")).strip().lower()
        if role in {"assistant", "agent", "model"}:
            role = "agent"
        elif role != "user":
            role = "message"
        if role == "user" and _is_google_save_request(content):
            continue
        author = "You" if role == "user" else "ArkAI"
        cleaned.append({"role": role, "author": author, "content": content})
    return cleaned

def _latest_google_save_content(cleaned_messages: list[dict[str, str]], role: str) -> str:
    role = role.lower()
    if role in {"assistant", "model"}:
        role = "agent"
    for message in reversed(cleaned_messages):
        if message.get("role") == role:
            return message.get("content", "")
    return ""

def _latest_google_save_exchange(cleaned_messages: list[dict[str, str]]) -> tuple[str, str, list[dict[str, str]]]:
    answer_index = -1
    for index in range(len(cleaned_messages) - 1, -1, -1):
        if cleaned_messages[index].get("role") == "agent":
            answer_index = index
            break

    if answer_index < 0:
        prompt_index = -1
        for index in range(len(cleaned_messages) - 1, -1, -1):
            if cleaned_messages[index].get("role") == "user":
                prompt_index = index
                break
        prompt = cleaned_messages[prompt_index]["content"] if prompt_index >= 0 else ""
        earlier_messages = [
            message for index, message in enumerate(cleaned_messages) if prompt_index < 0 or index < prompt_index
        ]
        return prompt, "", earlier_messages

    prompt_index = -1
    for index in range(answer_index - 1, -1, -1):
        if cleaned_messages[index].get("role") == "user":
            prompt_index = index
            break

    prompt = cleaned_messages[prompt_index]["content"] if prompt_index >= 0 else ""
    answer = cleaned_messages[answer_index]["content"]
    paired_indexes = {answer_index}
    if prompt_index >= 0:
        paired_indexes.add(prompt_index)
    earlier_messages = [
        message for index, message in enumerate(cleaned_messages) if prompt_index < 0 or index < prompt_index
    ]
    return prompt, answer, earlier_messages

def _has_google_save_answer(messages: list[dict[str, Any]]) -> bool:
    _, answer, _ = _latest_google_save_exchange(_google_save_messages(messages))
    return bool(answer)

def _strip_google_save_offer(text: str) -> str:
    """Remove the Tutor's closing save-offer from content being written to Docs."""
    lines = _clean_google_save_text(text).splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    while lines:
        tail = lines[-1].strip()
        normalized_tail = re.sub(r"\s+", " ", tail).lower()
        if not normalized_tail:
            lines.pop()
            continue
        if (
            "would you like" in normalized_tail
            and "save" in normalized_tail
            and ("google doc" in normalized_tail or "docs" in normalized_tail)
        ):
            lines.pop()
            while lines and not lines[-1].strip():
                lines.pop()
            if lines and lines[-1].strip() in {"---", "___", "***"}:
                lines.pop()
            continue
        break
    return "\n".join(lines).strip()

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
    if not cleaned_messages:
        return "No tutor content was available to save yet."

    prompt, answer, earlier_messages = _latest_google_save_exchange(cleaned_messages)
    if answer:
        return _strip_google_save_offer(answer) or answer

    return prompt or "No tutor response was found in this chat yet."

def _format_chat_messages_for_google_drive(messages: list[dict[str, Any]]) -> str:
    cleaned_messages = _google_save_messages(messages)
    lines = ["# ArkAI Tutor Notes", ""]
    if not cleaned_messages:
        lines.append("No tutor content was available to save yet.")
        return "\n".join(lines).strip()

    prompt, answer, earlier_messages = _latest_google_save_exchange(cleaned_messages)
    if prompt:
        lines.extend(["## Prompt", prompt, ""])
    if answer:
        lines.extend(["## Tutor response", answer, ""])
    if earlier_messages:
        lines.extend(["## Earlier context"])
        for message in earlier_messages[-6:]:
            lines.append(f"- **{message['author']}**: {_truncate_google_save_text(message['content'], 500)}")
    return "\n".join(lines).strip()

def _format_chat_messages_for_google_task(messages: list[dict[str, Any]]) -> str:
    cleaned_messages = _google_save_messages(messages)
    if not cleaned_messages:
        return "Created from ArkAI Tutor."
    prompt, answer, _ = _latest_google_save_exchange(cleaned_messages)
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
    prompt, answer, _ = _latest_google_save_exchange(cleaned_messages)
    parts = ["ArkAI Tutor study session."]
    if prompt:
        parts.extend(["", "Focus:", _truncate_google_save_text(prompt, 350)])
    if answer:
        parts.extend(["", "Notes:", _truncate_google_save_text(answer, 1200)])
    return "\n".join(parts).strip()

async def _get_tutor_chat_save_payload(
    user_id: str,
    session_id: str,
    client_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from .productivity_mcp_server import google_oauth_status

    oauth_status = await asyncio.to_thread(google_oauth_status, user_id)
    if not oauth_status.get("connected"):
        return {
            "status": "auth_required",
            "message": "Google saves is not connected for this signed-in ArkAI account.",
        }

    history = await asyncio.to_thread(get_chat_messages, user_id, session_id=session_id)
    if history.get("status") != "success":
        return {
            "status": "error",
            "message": history.get("message") or "Could not read the current Tutor chat.",
        }

    messages = history.get("messages") or []
    if client_messages and _has_google_save_answer(client_messages):
        messages = client_messages
    return {
        "status": "success",
        "messages": messages,
        "title": _chat_doc_title(messages),
        "note_text": _format_chat_messages_for_google_doc(messages),
        "drive_text": _format_chat_messages_for_google_drive(messages),
        "task_notes": _format_chat_messages_for_google_task(messages),
        "calendar_description": _format_chat_messages_for_google_calendar(messages),
    }


async def _save_tutor_chat_to_google_doc(
    user_id: str,
    session_id: str,
    client_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from .productivity_mcp_server import save_google_doc_note

    payload = await _get_tutor_chat_save_payload(user_id, session_id, client_messages=client_messages)
    if payload.get("status") != "success":
        return payload
    return await asyncio.to_thread(save_google_doc_note,
        user_id=user_id,
        title=payload["title"],
        note_text=payload["note_text"],
    )


async def _save_tutor_chat_to_google_drive(
    user_id: str,
    session_id: str,
    client_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from .productivity_mcp_server import save_text_file_to_drive

    payload = await _get_tutor_chat_save_payload(user_id, session_id, client_messages=client_messages)
    if payload.get("status") != "success":
        return payload
    return await asyncio.to_thread(save_text_file_to_drive,
        user_id=user_id,
        title=payload["title"],
        content=payload["drive_text"],
    )


async def _save_tutor_chat_to_google_task(
    user_id: str,
    session_id: str,
    client_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from .productivity_mcp_server import create_study_task

    payload = await _get_tutor_chat_save_payload(user_id, session_id, client_messages=client_messages)
    if payload.get("status") != "success":
        return payload
    return await asyncio.to_thread(create_study_task,
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

async def _save_tutor_chat_to_google_calendar(
    user_id: str,
    session_id: str,
    message: str,
    timezone_name: str,
    client_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from .productivity_mcp_server import create_calendar_event

    payload = await _get_tutor_chat_save_payload(user_id, session_id, client_messages=client_messages)
    if payload.get("status") != "success":
        return payload
    window = _calendar_window_from_message(message, timezone_name)
    if not window:
        return {
            "status": "needs_time",
            "message": "Tell me a date and time, for example: save this to Google Calendar tomorrow at 9am.",
        }
    start_time, end_time = window
    return await asyncio.to_thread(create_calendar_event, 
        user_id=user_id,
        event_title=payload["title"],
        start_time_iso=start_time,
        end_time_iso=end_time,
        description=payload["calendar_description"],
    )

async def _save_roadmap_sessions_to_google_calendar(user_id: str, message: str, timezone_name: str) -> dict[str, Any]:
    from .productivity_mcp_server import create_calendar_event, google_oauth_status

    oauth_status = await asyncio.to_thread(google_oauth_status, user_id)
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

    roadmap_result = await asyncio.to_thread(get_roadmap, user_id)
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
        result = await asyncio.to_thread(create_calendar_event, 
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


def _build_temporary_attachment_context(attachments: Any) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(attachments, list):
        return "", []

    context_parts: list[str] = []
    metadata: list[dict[str, Any]] = []
    total_text_chars = 0
    max_text_chars = 16000

    for raw_item in attachments[:3]:
        if not isinstance(raw_item, dict):
            continue
        name = str(raw_item.get("name", "attachment.txt")).strip() or "attachment.txt"
        mime_type = str(raw_item.get("mimeType", "")).strip()
        data_base64 = str(raw_item.get("dataBase64", "")).strip()
        size_bytes = int(raw_item.get("sizeBytes") or 0)
        if not data_base64 or size_bytes > 5 * 1024 * 1024:
            continue
        try:
            blob = _decode_base64(data_base64)
            extracted = _extract_text_from_payload(name, mime_type, blob, "").strip()
        except Exception:
            LOGGER.exception("Could not read temporary Tutor attachment %s", name)
            extracted = ""

        metadata.append(
            {
                "name": name,
                "mime_type": mime_type,
                "size_bytes": size_bytes,
                "has_extracted_text": bool(extracted),
            }
        )
        if not extracted:
            context_parts.append(
                f"Attachment: {name}\nNo extractable text was found. Ask the user to paste the relevant text if needed."
            )
            continue

        remaining_chars = max_text_chars - total_text_chars
        if remaining_chars <= 0:
            break
        snippet = extracted[:remaining_chars]
        total_text_chars += len(snippet)
        context_parts.append(f"Attachment: {name}\n{snippet}")

    if not context_parts:
        return "", metadata

    return (
        "\n\nTemporary attachments for this Tutor message. Use them for this response only; "
        "do not treat them as saved learner materials unless the user asks to save them.\n\n"
        + "\n\n---\n\n".join(context_parts),
        metadata,
    )


async def _run_agent(
    user_id: str,
    session_id: str,
    message: str,
    user_timezone: str = "",
    selected_material_ids: list[str] | None = None,
) -> str:
    active_runner = _get_runner()
    # Assuming active_runner has session_service
    session_service = active_runner.session_service
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

api_router = APIRouter()

def _set_cookie(response: Response, name: str, value: str, max_age: int = 60 * 60 * 24 * 365, http_only: bool = True, request: Request = None):
    secure = False
    if request:
        forwarded_proto = str(request.headers.get("X-Forwarded-Proto", "")).strip().lower()
        if forwarded_proto == "https" or request.url.scheme == "https":
            secure = True
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=http_only,
        secure=secure,
        samesite="lax",
        path="/"
    )

def _clear_cookie(response: Response, name: str, http_only: bool = True, request: Request = None):
    _set_cookie(response, name, "", max_age=0, http_only=http_only, request=request)

async def _resolve_request_context(
    request: Request,
    response: Response,
    payload: Any = None,
    *,
    reset_identity: bool = False,
    reset_session: bool = False,
    requested_session_id: str = "",
    ignore_auth: bool = False,
) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump()
    else:
        payload = dict(payload or {})
    if "userId" not in payload or not payload["userId"]:
        query_user_id = request.query_params.get("userId", "").strip()
        if query_user_id:
            payload["userId"] = query_user_id
    if ignore_auth:
        authenticated_user_id = ""
    else:
        authenticated_user_id, _ = await asyncio.to_thread(_resolve_authenticated_user, payload, request)
    
    client_id = request.cookies.get(CLIENT_COOKIE_NAME, "")
    session_id = requested_session_id or request.cookies.get(SESSION_COOKIE_NAME, "")
    
    identity = await asyncio.to_thread(
        get_or_create_browser_identity,
        client_id=client_id,
        authenticated_user_id=authenticated_user_id,
        reset_identity=reset_identity,
    )
    session = await asyncio.to_thread(
        get_or_create_chat_session,
        client_id=str(identity["client_id"]),
        user_id=str(identity["user_id"]),
        session_id=session_id,
        reset_session=reset_session,
    )

    _set_cookie(response, CLIENT_COOKIE_NAME, str(identity["client_id"]), request=request)
    _set_cookie(response, SESSION_COOKIE_NAME, str(session["session_id"]), request=request)

    user_id = str(identity["user_id"])
    return {
        "user_id": user_id,
        "session_id": str(session["session_id"]),
        "is_anonymous": user_id.startswith("guest:"),
        "display_name": _display_name_for_user(user_id),
    }

@api_router.get("/api/health")
async def api_health():
    return {"status": "ok"}

@api_router.get("/api/config")
async def api_config():
    return {
        "firebase": _firebase_web_config(),
        "authMode": "firebase" if _firebase_web_config() else "email_fallback",
    }

@api_router.get("/api/session")
async def api_get_session(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    return {
        "status": "success",
        "userId": context["user_id"],
        "sessionId": context["session_id"],
        "displayName": context["display_name"],
        "isAnonymous": context["is_anonymous"],
    }

@api_router.get("/api/system-status")
async def api_system_status(request: Request):
    return _system_status(request)

@api_router.get("/api/demo-kit")
async def api_demo_kit(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    return await asyncio.to_thread(get_demo_kit, context["user_id"])

@api_router.get("/api/learner-state")
async def api_learner_state(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    return await asyncio.to_thread(get_learner_state, context["user_id"])

@api_router.get("/api/mastery")
async def api_mastery(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    return await asyncio.to_thread(get_mastery_snapshot, context["user_id"])

@api_router.get("/api/roadmap")
async def api_get_roadmap(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    result = await asyncio.to_thread(get_roadmap, context["user_id"])
    if result.get("status") != "success":
        response.status_code = HTTPStatus.NOT_FOUND
    return result

@api_router.get("/api/roadmaps")
async def api_list_roadmaps(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    return await asyncio.to_thread(list_roadmaps, context["user_id"])

@api_router.post("/api/roadmap/delete-saved")
async def api_delete_saved_roadmap(request: Request, response: Response, payload: RoadmapDeleteSavedRequest):
    context = await _resolve_context(request, response, payload)
    result = await asyncio.to_thread(
        delete_saved_roadmap,
        context["user_id"],
        str(payload.roadmapId or "").strip(),
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/roadmap/delete-all-saved")
async def api_delete_all_saved_roadmaps(request: Request, response: Response, payload: ApiRequest):
    context = await _resolve_context(request, response, payload)
    result = await asyncio.to_thread(delete_all_saved_roadmaps, context["user_id"])
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/roadmap/saved-session/update")
async def api_saved_roadmap_session_update(
    request: Request,
    response: Response,
    payload: SavedRoadmapSessionUpdateRequest,
):
    context = await _resolve_context(request, response, payload)
    result = await asyncio.to_thread(
        update_saved_roadmap_session,
        user_id=context["user_id"],
        roadmap_id=str(payload.roadmapId or "").strip(),
        phase_id=str(payload.phaseId or "").strip(),
        session_id=str(payload.sessionId or "").strip(),
        status=str(payload.status or "").strip(),
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.get("/api/materials")
async def api_materials(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    return await asyncio.to_thread(list_learning_materials, context["user_id"])

@api_router.get("/api/chat/sessions")
async def api_chat_sessions(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    result = await asyncio.to_thread(list_chat_sessions, context["user_id"], limit=30)
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.get("/api/chat/messages")
async def api_chat_messages(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    session_id = request.query_params.get("sessionId", "").strip()
    result = await asyncio.to_thread(get_chat_messages, context["user_id"], session_id=session_id)
    if result.get("status") != "success":
        response.status_code = HTTPStatus.NOT_FOUND
    return result

@api_router.get("/api/intervention")
async def api_intervention(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    return await asyncio.to_thread(get_intervention_plan, context["user_id"])

@api_router.get("/api/evaluation")
async def api_evaluation(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    return await asyncio.to_thread(get_evaluation_snapshot, context["user_id"])

@api_router.get("/api/google/status")
async def api_google_status(request: Request, response: Response):
    try:
        context = await _resolve_request_context(request, response)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    oauth_setup_ready = (BASE_DIR / "ark_learning_agent" / "credentials.json").is_file() and bool(_resolved_auth_callback_url())
    firebase_token_connect_ready = _firebase_web_config() is not None
    google_saves_setup_ready = oauth_setup_ready or firebase_token_connect_ready
    if context["is_anonymous"]:
        return {
            "status": "success",
            "connected": False,
            "setup_ready": google_saves_setup_ready,
            "message": "Sign in with Google to connect saves.",
        }
    from .productivity_mcp_server import google_oauth_status
    result = await asyncio.to_thread(google_oauth_status, context["user_id"])
    if result.get("connected"):
        result["setup_ready"] = google_saves_setup_ready
        return result
    if not google_saves_setup_ready:
        return {
            "status": "success",
            "connected": False,
            "setup_ready": False,
            "message": "Google saves is not configured on this server.",
        }
    result["setup_ready"] = True
    return result


@api_router.post("/api/auth/session")
async def api_auth_session(request: Request, response: Response, payload: ApiRequest = None):
    payload = payload or ApiRequest()
    id_token = str(payload.idToken or "").strip() or _authorization_token(request.headers)
    if not id_token:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail={"error": "Missing Firebase ID token."})
    try:
        user_id = await asyncio.to_thread(_verify_firebase_id_token_email, id_token)
        session_cookie = await asyncio.to_thread(_create_firebase_session_cookie, id_token)
        _set_cookie(response, FIREBASE_SESSION_COOKIE_NAME, session_cookie, max_age=FIREBASE_SESSION_MAX_AGE_SECONDS, request=request)
        context = await _resolve_request_context(request, response, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    return {
        "status": "success",
        "userId": user_id,
        "sessionId": context["session_id"],
        "displayName": context["display_name"],
        "isAnonymous": False,
    }

@api_router.post("/api/auth/logout")
async def api_auth_logout(request: Request, response: Response, payload: ApiRequest = None):
    payload = payload or ApiRequest()
    _clear_cookie(response, FIREBASE_SESSION_COOKIE_NAME, request=request)
    
    reset_identity = True
    if payload.resetIdentity is not None:
        reset_identity = payload.resetIdentity
    reset_session = True
    if payload.resetSession is not None:
        reset_session = payload.resetSession
        
    context = await _resolve_request_context(
        request, response, payload,
        reset_identity=reset_identity,
        reset_session=reset_session,
        ignore_auth=True,
    )
    return {
        "status": "success",
        "userId": context["user_id"],
        "sessionId": context["session_id"],
        "displayName": context["display_name"],
        "isAnonymous": context["is_anonymous"],
    }

@api_router.post("/api/google/connect")
async def api_google_connect(request: Request, response: Response, payload: GoogleConnectRequest = None):
    payload = payload or GoogleConnectRequest()
    try:
        context = await _resolve_request_context(request, response, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    if context["is_anonymous"]:
        response.status_code = HTTPStatus.UNAUTHORIZED
        return {
            "status": "error",
            "message": "Sign in with Google before connecting Docs, Calendar, and Tasks.",
        }
    from .productivity_mcp_server import get_google_authorization_url
    result = await asyncio.to_thread(
        get_google_authorization_url,
        context["user_id"],
        bool(payload.forceReconnect),
    )
    if result.get("status") not in {"success", "auth_required"}:
        response.status_code = HTTPStatus.BAD_REQUEST
    return result


@api_router.post("/api/google/connect-token")
async def api_google_connect_token(request: Request, response: Response, payload: GoogleTokenConnectRequest = None):
    payload = payload or GoogleTokenConnectRequest()
    try:
        context = await _resolve_request_context(request, response, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    if context["is_anonymous"]:
        response.status_code = HTTPStatus.UNAUTHORIZED
        return {
            "status": "error",
            "message": "Sign in with Google before connecting Docs, Calendar, and Tasks.",
        }
    from .productivity_mcp_server import persist_google_access_token
    result = await asyncio.to_thread(
        persist_google_access_token,
        context["user_id"],
        str(payload.accessToken or "").strip(),
        payload.expiresIn,
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result


async def _resolve_context(request: Request, response: Response, payload: ApiRequest):
    try:
        context = await _resolve_request_context(
            request, response, payload,
            reset_identity=payload.resetIdentity or False,
            reset_session=payload.resetSession or False,
            requested_session_id=str(payload.sessionId or "").strip(),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED, detail={"error": str(exc)})
    return context

@api_router.post("/api/session")
async def api_post_session(request: Request, response: Response, payload: ApiRequest):
    context = await _resolve_context(request, response, payload)
    return {
        "status": "success",
        "userId": context["user_id"],
        "sessionId": context["session_id"],
        "displayName": context["display_name"],
        "isAnonymous": context["is_anonymous"],
    }

@api_router.post("/api/chat/delete")
async def api_chat_delete(request: Request, response: Response, payload: ChatDeleteRequest):
    context = await _resolve_context(request, response, payload)
    result = await asyncio.to_thread(delete_chat_session, 
        user_id=context["user_id"],
        session_id=str(payload.targetSessionId or "").strip(),
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/chat/delete-all")
async def api_chat_delete_all(request: Request, response: Response, payload: ApiRequest):
    context = await _resolve_context(request, response, payload)
    result = await asyncio.to_thread(delete_all_chat_sessions, user_id=context["user_id"])
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/diagnostic/start")
async def api_diagnostic_start(request: Request, response: Response, payload: DiagnosticStartRequest):
    context = await _resolve_context(request, response, payload)
    app_metrics["diagnostics_started"] += 1
    result = await asyncio.to_thread(create_assessment, 
        user_id=context["user_id"],
        topic=str(payload.topic or "").strip(),
        assessment_type=str(payload.assessmentType or "diagnostic").strip() or "diagnostic",
        level=str(payload.level or "beginner").strip() or "beginner",
        goal=str(payload.goal or "").strip(),
        available_time=payload.availableTime,
        learning_style=str(payload.learningStyle or "balanced").strip() or "balanced",
        question_count=payload.questionCount or 5,
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/diagnostic/submit")
async def api_diagnostic_submit(request: Request, response: Response, payload: DiagnosticSubmitRequest):
    context = await _resolve_context(request, response, payload)
    app_metrics["diagnostics_submitted"] += 1
    result = await asyncio.to_thread(submit_assessment, 
        user_id=context["user_id"],
        assessment_id=str(payload.assessmentId or "").strip(),
        answers=payload.answers or {},
        confidence_by_question=payload.confidenceByQuestion or {},
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/roadmap/generate")
async def api_roadmap_generate(request: Request, response: Response, payload: RoadmapGenerateRequest):
    context = await _resolve_context(request, response, payload)
    app_metrics["roadmaps_generated"] += 1
    result = await asyncio.to_thread(build_or_update_roadmap, 
        user_id=context["user_id"],
        topic=str(payload.topic or "").strip(),
        goal=str(payload.goal or "").strip(),
        level=str(payload.level or "").strip(),
        available_time=payload.availableTime,
        deadline_days=payload.deadlineDays or 14,
        start_date=str(payload.startDate or "").strip(),
        force_rebuild=bool(payload.forceRebuild),
        revision_reason=str(payload.revisionReason or "").strip(),
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/roadmap/delete")
async def api_roadmap_delete(request: Request, response: Response, payload: ApiRequest):
    context = await _resolve_context(request, response, payload)
    result = await asyncio.to_thread(delete_roadmap, user_id=context["user_id"])
    if result.get("status") != "success":
        response.status_code = HTTPStatus.NOT_FOUND
    return result

@api_router.post("/api/roadmap/session/update")
async def api_roadmap_session_update(request: Request, response: Response, payload: RoadmapSessionUpdateRequest):
    context = await _resolve_context(request, response, payload)
    app_metrics["roadmap_updates"] += 1
    result = await asyncio.to_thread(update_roadmap_session, 
        user_id=context["user_id"],
        phase_id=str(payload.phaseId or "").strip(),
        session_id=str(payload.sessionId or "").strip(),
        status=str(payload.status or "").strip(),
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/roadmap/save-google-tasks")
async def api_roadmap_save_google_tasks(request: Request, response: Response, payload: ApiRequest):
    context = await _resolve_context(request, response, payload)
    from .productivity_mcp_server import create_roadmap_tasks, google_oauth_status
    user_id = context["user_id"]
    oauth_status = await asyncio.to_thread(google_oauth_status, user_id)
    if not oauth_status.get("connected"):
        return {
            "status": "auth_required",
            "message": "Connect Google saves from the account menu before saving roadmap tasks.",
        }
    result = await asyncio.to_thread(create_roadmap_tasks, user_id=user_id, include_due_dates=False)
    if result.get("status") not in {"success", "auth_required"}:
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/roadmap/session/save-calendar")
async def api_roadmap_session_save_calendar(request: Request, response: Response, payload: RoadmapSaveCalendarRequest):
    context = await _resolve_context(request, response, payload)
    from .productivity_mcp_server import create_calendar_event, google_oauth_status
    user_id = context["user_id"]
    oauth_status = await asyncio.to_thread(google_oauth_status, user_id)
    if not oauth_status.get("connected"):
        return {
            "status": "auth_required",
            "message": "Connect Google saves from the account menu before saving calendar events.",
        }
    title = str(payload.title or "").strip() or "Roadmap study session"
    focus = str(payload.focus or "").strip()
    phase_title = str(payload.phaseTitle or "").strip()
    phase_goal = str(payload.phaseGoal or "").strip()
    start_time = str(payload.startTime or "").strip()
    end_time = str(payload.endTime or "").strip()
    if not start_time or not end_time:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Choose a start time first.")

    description_parts = [
        f"Focus: {focus}" if focus else "",
        f"Phase: {phase_title}" if phase_title else "",
        phase_goal,
        "Created from ArkAI roadmap.",
    ]
    result = await asyncio.to_thread(create_calendar_event, 
        user_id=user_id,
        event_title=f"Study: {title}",
        start_time_iso=start_time,
        end_time_iso=end_time,
        description="\n".join(part for part in description_parts if part),
    )
    if result.get("status") not in {"success", "auth_required"}:
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/materials/upload")
async def api_materials_upload(request: Request, response: Response, payload: MaterialsUploadRequest):
    context = await _resolve_context(request, response, payload)
    app_metrics["materials_uploaded"] += 1
    result = await asyncio.to_thread(save_learning_material, 
        user_id=context["user_id"],
        name=str(payload.name or "").strip(),
        mime_type=str(payload.mimeType or "").strip(),
        data_base64=str(payload.dataBase64 or "").strip(),
        pasted_text=str(payload.pastedText or "").strip(),
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/materials/tutor")
async def api_materials_tutor(request: Request, response: Response, payload: MaterialsTutorRequest):
    context = await _resolve_context(request, response, payload)
    app_metrics["materials_tutored"] += 1
    result = await asyncio.to_thread(tutor_from_materials, 
        user_id=context["user_id"],
        query=str(payload.query or "").strip(),
        material_ids=[str(item) for item in (payload.materialIds or []) if str(item).strip()],
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/materials/mock-test")
async def api_materials_mock_test(request: Request, response: Response, payload: MaterialsMockTestRequest):
    context = await _resolve_context(request, response, payload)
    result = await asyncio.to_thread(create_mock_test_from_materials, 
        user_id=context["user_id"],
        material_ids=[str(item) for item in (payload.materialIds or []) if str(item).strip()],
        topic=str(payload.topic or "").strip(),
        level=str(payload.level or "beginner").strip() or "beginner",
        goal=str(payload.goal or "").strip(),
        question_count=payload.questionCount or 5,
        structure=str(payload.structure or "").strip(),
        sample_style=str(payload.sampleStyle or "").strip(),
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/materials/delete")
async def api_materials_delete(request: Request, response: Response, payload: MaterialDeleteRequest):
    context = await _resolve_context(request, response, payload)
    result = await asyncio.to_thread(delete_learning_material, 
        user_id=context["user_id"],
        material_id=str(payload.materialId or "").strip(),
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/materials/delete-all")
async def api_materials_delete_all(request: Request, response: Response, payload: ApiRequest):
    context = await _resolve_context(request, response, payload)
    result = await asyncio.to_thread(delete_all_learning_materials, user_id=context["user_id"])
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/history/delete")
async def api_history_delete(request: Request, response: Response, payload: HistoryDeleteRequest):
    context = await _resolve_context(request, response, payload)
    result = await asyncio.to_thread(delete_learning_history_item, 
        user_id=context["user_id"],
        record_id=str(payload.recordId or "").strip(),
    )
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/history/delete-all")
async def api_history_delete_all(request: Request, response: Response, payload: ApiRequest):
    context = await _resolve_context(request, response, payload)
    result = await asyncio.to_thread(delete_all_learning_history, user_id=context["user_id"])
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/report/generate")
async def api_report_generate(request: Request, response: Response, payload: ApiRequest):
    context = await _resolve_context(request, response, payload)
    app_metrics["reports_generated"] += 1
    result = await asyncio.to_thread(generate_weekly_report, context["user_id"])
    if result.get("status") != "success":
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/report/save-google-doc")
async def api_report_save_google_doc(request: Request, response: Response, payload: ReportSaveDocRequest):
    context = await _resolve_context(request, response, payload)
    app_metrics["reports_saved_to_docs"] += 1
    from .productivity_mcp_server import google_oauth_status, save_weekly_report_doc
    user_id = context["user_id"]
    oauth_status = await asyncio.to_thread(google_oauth_status, user_id)
    if not oauth_status.get("connected"):
        return {
            "status": "auth_required",
            "message": "Connect Google saves from the account menu before saving reports.",
        }
    result = await asyncio.to_thread(save_weekly_report_doc, 
        user_id=user_id,
        title=str(payload.title or "").strip(),
    )
    if result.get("status") not in {"success", "auth_required"}:
        response.status_code = HTTPStatus.BAD_REQUEST
    return result

@api_router.post("/api/assessment/save-google-doc")
async def api_assessment_save_google_doc(request: Request, response: Response, payload: AssessmentSaveDocRequest):
    context = await _resolve_context(request, response, payload)
    from .productivity_mcp_server import google_oauth_status, save_assessment_doc
    user_id = context["user_id"]
    oauth_status = await asyncio.to_thread(google_oauth_status, user_id)
    if not oauth_status.get("connected"):
        return {
            "status": "auth_required",
            "message": "Connect Google saves from the account menu before saving assessments.",
        }
    result = await asyncio.to_thread(save_assessment_doc, 
        user_id=user_id,
        assessment_id=str(payload.assessmentId or "").strip(),
        title=str(payload.title or "").strip(),
    )
    if result.get("status") not in {"success", "auth_required"}:
        response.status_code = HTTPStatus.BAD_REQUEST
    return result


@api_router.post("/api/chat")
async def api_chat(request: Request, response: Response, payload: ChatRequest):
    context = await _resolve_context(request, response, payload)
    
    user_id = context["user_id"]
    session_id = context["session_id"]
    message = str(payload.message or "").strip()
    user_timezone = str(payload.timezone or "").strip()
    selected_material_ids = [
        str(item) for item in (payload.selectedMaterialIds or []) if str(item).strip()
    ]
    input_mode = str(payload.inputMode or "").strip().lower()
    temporary_attachment_context, temporary_attachment_metadata = _build_temporary_attachment_context(
        payload.temporaryAttachments
    )

    if not message and not temporary_attachment_context:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Missing message.")
        
    agent_message = (
        f"{message}\n\n{temporary_attachment_context}".strip()
        if temporary_attachment_context
        else message
    )

    try:
        app_metrics["chat_requests"] += 1
        await asyncio.to_thread(append_chat_message, 
            user_id=user_id,
            session_id=session_id,
            role="user",
            author="user",
            content=message,
            metadata={
                "timezone": user_timezone,
                "selected_material_ids": selected_material_ids,
                "input_mode": input_mode,
                "temporary_attachments": temporary_attachment_metadata,
            },
        )
        if _is_google_save_request(message):
            client_messages = payload.clientMessages or []
            try:
                if _is_google_drive_save_request(message):
                    save_result = await _save_tutor_chat_to_google_drive(
                        user_id=user_id,
                        session_id=session_id,
                        client_messages=client_messages,
                    )
                elif _is_google_task_save_request(message):
                    save_result = await _save_tutor_chat_to_google_task(
                        user_id=user_id,
                        session_id=session_id,
                        client_messages=client_messages,
                    )
                elif _is_google_calendar_save_request(message):
                    if _is_roadmap_calendar_request(message):
                        save_result = await _save_roadmap_sessions_to_google_calendar(
                            user_id=user_id,
                            message=message,
                            timezone_name=user_timezone,
                        )
                    else:
                        save_result = await _save_tutor_chat_to_google_calendar(
                            user_id=user_id,
                            session_id=session_id,
                            message=message,
                            timezone_name=user_timezone,
                            client_messages=client_messages,
                        )
                else:
                    save_result = await _save_tutor_chat_to_google_doc(
                        user_id=user_id,
                        session_id=session_id,
                        client_messages=client_messages,
                    )
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
                if context["is_anonymous"]:
                    reply = (
                        "You are still using a private guest session, so I cannot save to Google Docs yet. "
                        "Use Continue with Google first, then connect Google saves from the account menu and retry."
                    )
                else:
                    reply = (
                        "Google saves is still not connected for the signed-in ArkAI account I can verify. "
                        "Open the account menu, connect Google saves again, then retry."
                    )
            else:
                reply = f"I could not complete that Google save: {save_result.get('message') or 'unknown error'}"
            await asyncio.to_thread(append_chat_message, 
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                author="ARKAI",
                content=reply,
            )
            return {
                "reply": reply,
                "session": {
                    "userId": context["user_id"],
                    "sessionId": context["session_id"],
                    "displayName": context["display_name"],
                    "isAnonymous": context["is_anonymous"],
                },
            }
            
        if _remote_agent_base_url():
            reply = await asyncio.to_thread(
                _run_agent_remote,
                user_id=user_id,
                session_id=session_id,
                message=agent_message,
                user_timezone=user_timezone,
                selected_material_ids=selected_material_ids,
            )
        else:
            reply = await asyncio.wait_for(
                _run_agent(
                    user_id=user_id,
                    session_id=session_id,
                    message=agent_message,
                    user_timezone=user_timezone,
                    selected_material_ids=selected_material_ids,
                ),
                timeout=_remote_agent_timeout_seconds(),
            )
            
        await asyncio.to_thread(append_chat_message, 
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            author="ARKAI",
            content=reply,
        )
    except TimeoutError:
        raise HTTPException(status_code=HTTPStatus.GATEWAY_TIMEOUT, detail={"error": "Agent request timed out."})
    except Exception as exc:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail={"error": f"Agent request failed: {exc}"})

    if input_mode == "voice":
        try:
            from .learner_state import save_learning_progress

            await asyncio.to_thread(save_learning_progress, 
                user_id=user_id,
                topic="voice_tutor",
                activity_type="voice_session",
                notes=message[:500],
                score=None,
            )
        except Exception:
            pass

    return {
        "reply": reply,
        "session": {
            "userId": context["user_id"],
            "sessionId": context["session_id"],
            "displayName": context["display_name"],
            "isAnonymous": context["is_anonymous"],
        },
    }
