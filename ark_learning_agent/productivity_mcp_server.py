import os
from dotenv import load_dotenv
import datetime
import json
from pathlib import Path
import re
import secrets
import zoneinfo
from mcp.server.fastmcp import FastMCP

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

import firebase_admin
from firebase_admin import firestore
from google.cloud import firestore as google_cloud_firestore

try:
    from learner_state import (
        generate_weekly_report,
        get_firestore_client,
        get_roadmap,
        list_study_notes,
        save_study_note,
    )
except ImportError:
    from .learner_state import (
        generate_weekly_report,
        get_firestore_client,
        get_roadmap,
        list_study_notes,
        save_study_note,
    )

mcp = FastMCP("productivity-tools")

BASE_DIR = Path(__file__).resolve().parent
# Load repo root .env first, then package .env (package wins on duplicate keys).
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env", override=True)

def _running_on_cloud_run() -> bool:
    """Cloud Run sets K_SERVICE; Cloud Functions Gen2 on Cloud Run may set FUNCTION_TARGET."""
    return bool(os.environ.get("K_SERVICE"))


db = get_firestore_client()

from pygments import lex
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.token import Token

CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"
USER_GOOGLE_TOKENS_DIR = BASE_DIR / "user_google_tokens"
AUTH_CALLBACK_CREDENTIAL_PATHS = (
    CREDENTIALS_PATH,
    BASE_DIR.parent / "auth_function" / "credentials.json",
)

SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file'
]

# Google matches redirect_uri byte-for-byte on both authorize and token steps.
DEFAULT_LOCAL_OAUTH_PORT = 8765


def _google_oauth_prompt() -> str:
    """Force account picker + consent so users always see Google sign-in and scope approval."""
    return (os.environ.get("GOOGLE_OAUTH_PROMPT") or "select_account consent").strip() or "select_account consent"


def _production_https_redirect_uri_from_secrets(path: Path) -> str | None:
    """First https redirect URI from client secrets (must match Google Cloud Console)."""
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        web = cfg.get("web") or {}
        for u in web.get("redirect_uris") or []:
            u = (u or "").strip()
            if u.startswith("https://"):
                return u
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return None


def _cloud_oauth_redirect_uri() -> str:
    """Same URI must be used by the MCP (authorize) and the callback service (token)."""
    configured_uris = [
        uri
        for uri in (
            _production_https_redirect_uri_from_secrets(path)
            for path in AUTH_CALLBACK_CREDENTIAL_PATHS
        )
        if uri
    ]

    for key in ("OAUTH_REDIRECT_URI", "AUTH_CALLBACK_URL"):
        env_uri = (os.environ.get(key) or "").strip()
        if env_uri and (not configured_uris or env_uri in configured_uris):
            return env_uri

    if configured_uris:
        return configured_uris[0]
    return ""

def _safe_user_id_for_path(user_id: str) -> str:
    return "".join(c if c.isalnum() or c in "@._-" else "_" for c in str(user_id).strip())[:200]


def _user_google_oauth_doc(user_id: str):
    if not db:
        return None
    return (
        db.collection("users")
        .document(str(user_id).strip())
        .collection("integrations")
        .document("google_oauth")
    )

def _google_oauth_state_doc(state: str):
    if not db:
        return None
    return db.collection("google_oauth_states").document(str(state).strip())

def _user_google_token_path(user_id: str) -> Path:
    USER_GOOGLE_TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    return USER_GOOGLE_TOKENS_DIR / f"{_safe_user_id_for_path(user_id)}.json"

def _credentials_from_payload(payload: dict):
    try:
        return Credentials.from_authorized_user_info(payload, SCOPES)
    except ValueError:
        token = str(payload.get("token") or "").strip()
        if not token:
            raise
        expiry = None
        expiry_value = str(payload.get("expiry") or "").strip()
        if expiry_value:
            try:
                expiry = datetime.datetime.fromisoformat(expiry_value.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                expiry = None
        return Credentials(
            token=token,
            scopes=payload.get("scopes") or SCOPES,
            expiry=expiry,
        )

def _load_google_credentials_from_disk(user_id: str):
    path = _user_google_token_path(user_id)
    if path.is_file():
        return _credentials_from_payload(json.loads(path.read_text(encoding="utf-8")))
    if os.environ.get("ALLOW_LEGACY_SHARED_TOKEN") == "1" and TOKEN_PATH.is_file():
        return _credentials_from_payload(json.loads(TOKEN_PATH.read_text(encoding="utf-8")))
    return None

def _persist_google_credentials(user_id: str, creds: Credentials) -> None:
    payload = json.loads(creds.to_json())
    if db:
        db.collection("users").document(str(user_id).strip()).set(
            {
                "user_id": str(user_id).strip(),
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        _user_google_oauth_doc(user_id).set(
            {
                **payload,
                "provider": "google_oauth",
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
        )
    else:
        path = _user_google_token_path(user_id)
        path.write_text(creds.to_json(), encoding="utf-8")

def persist_google_access_token(user_id: str, access_token: str, expires_in: int | None = None) -> dict:
    normalized_user_id = _normalize_oauth_user_id(user_id)
    token = str(access_token or "").strip()
    if not normalized_user_id:
        return {"status": "error", "message": "Missing signed-in user."}
    if not token:
        return {"status": "error", "message": "Missing Google access token."}

    expires_at = None
    if expires_in:
        try:
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=max(60, int(expires_in)))
        except (TypeError, ValueError):
            expires_at = None

    creds = Credentials(
        token=token,
        scopes=SCOPES,
        expiry=expires_at,
    )
    _persist_google_credentials(normalized_user_id, creds)
    return {
        "status": "success",
        "connected": True,
        "message": "Google saves connected.",
    }

def _create_oauth_state(user_id: str) -> str:
    normalized_user_id = _normalize_oauth_user_id(user_id)
    if not db:
        raise RuntimeError("Google OAuth state storage is unavailable.")
    state = secrets.token_urlsafe(32)
    _google_oauth_state_doc(state).set(
        {
            "user_id": normalized_user_id,
            "created_at": firestore.SERVER_TIMESTAMP,
            "status": "pending",
        }
    )
    return state

def google_oauth_status(user_id: str) -> dict:
    normalized_user_id = _normalize_oauth_user_id(user_id)
    if not normalized_user_id:
        return {"status": "error", "message": "Missing signed-in user."}

    has_credentials = False
    if db:
        doc_ref = _user_google_oauth_doc(normalized_user_id)
        if doc_ref:
            doc = doc_ref.get()
            has_credentials = doc.exists
    
    if not has_credentials:
        has_credentials = _user_google_token_path(normalized_user_id).is_file()

    return {
        "status": "success",
        "connected": bool(has_credentials),
        "message": "Google saves connected." if has_credentials else "Google saves are not connected.",
    }

def get_google_authorization_url(user_id: str, force_reconnect: bool = False) -> dict:
    normalized_user_id = _normalize_oauth_user_id(user_id)
    if not normalized_user_id:
        return {"status": "error", "message": "Sign in before connecting Google saves."}
    if normalized_user_id.startswith("guest:"):
        return {"status": "error", "message": "Sign in with Google before connecting Docs, Calendar, and Tasks."}

    existing = google_oauth_status(normalized_user_id)
    if existing.get("connected") and not force_reconnect:
        return {"status": "success", "connected": True, "message": "Google saves already connected."}

    if not db:
        return {
            "status": "error",
            "message": "Google saves are not ready because Firestore state storage is unavailable.",
        }

    if not CREDENTIALS_PATH.is_file():
        return {
            "status": "error",
            "message": "Google OAuth is not configured: credentials.json is missing.",
        }

    auth_url = _cloud_oauth_redirect_uri()
    if not auth_url:
        return {
            "status": "error",
            "message": "AUTH_CALLBACK_URL is missing. Configure the Google OAuth callback URL first.",
        }

    with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
        client_config = json.load(f)

    oauth_state = _create_oauth_state(normalized_user_id)
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        state=oauth_state,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = auth_url
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        prompt=_google_oauth_prompt(),
    )
    return {
        "status": "auth_required",
        "connected": False,
        "authorization_url": authorization_url,
        "message": "Open Google to allow ArkAI saves for Docs, Calendar, and Tasks.",
    }

def _oauth_via_local_browser(user_id: str):
    """Interactive Google sign-in for this machine; persists tokens for user_id.

    Uses a fixed loopback port so Authorized redirect URIs can match (port=0 is random).
    Register exactly: http://127.0.0.1:<port>/ in Google Cloud Console (trailing slash).
    """
    port = int(os.environ.get("GOOGLE_OAUTH_LOCAL_PORT", str(DEFAULT_LOCAL_OAUTH_PORT)))
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(
        host="127.0.0.1",
        port=port,
        prompt=_google_oauth_prompt(),
        access_type="offline",
        open_browser=True,
        redirect_uri_trailing_slash=True,
    )
    _persist_google_credentials(user_id, creds)
    return creds

def _normalize_oauth_user_id(user_id: str) -> str:
    return str(user_id or "").strip().lower()


def get_google_credentials(user_id):
    normalized_user_id = _normalize_oauth_user_id(user_id)
    if not normalized_user_id:
        return {
            "status": "error",
            "message": "Missing Google authorization identity. Use the active ARKAI app user_id or the Gmail the user already provided for Google authorization."
        }

    creds = None
    if db:
        doc = _user_google_oauth_doc(normalized_user_id).get()
        if doc.exists:
            creds = _credentials_from_payload(doc.to_dict() or {})
    else:
        creds = _load_google_credentials_from_disk(normalized_user_id)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                _persist_google_credentials(normalized_user_id, creds)
                return creds
            except Exception:
                pass

        if not CREDENTIALS_PATH.is_file():
            return {
                "status": "error",
                "message": (
                    "Google OAuth is not configured: credentials.json is missing next to the MCP server. "
                    "Add a Google Cloud OAuth client JSON file there."
                ),
            }

        # Hosted ADK on Cloud Run cannot run loopback OAuth; tokens after login live in Firestore.
        if _running_on_cloud_run() and not db:
            return {
                "status": "error",
                "message": (
                    "Google Docs/Calendar/Tasks need Firestore on this Cloud Run service. "
                    "Firebase Admin did not start: set GOOGLE_CLOUD_PROJECT to your GCP project ID in Cloud Run env vars, "
                    "enable the Firestore API, and grant this service's runtime service account the role "
                    "'Cloud Datastore User' (or roles that allow Firestore read/write). "
                    "Redeploy; the same project should hold your OAuth callback and Firestore database."
                ),
            }

        return {
            "status": "auth_required",
            "message": (
                "Connect Google saves from the ArkAI account menu before using Docs, Calendar, or Tasks. "
                "For security, ArkAI only connects saves after the currently signed-in account grants permission."
            ),
        }

    return creds

def pygments_token_to_docs_color(token_type):
    def rgb(r, g, b):
        return {'color': {'rgbColor': {'red': r/255.0, 'green': g/255.0, 'blue': b/255.0}}}
    
    if token_type in Token.Keyword:
        return rgb(0, 0, 255) # Blue
    elif token_type in Token.Name.Function:
        return rgb(120, 0, 0) # Dark red
    elif token_type in Token.Name.Class:
        return rgb(0, 120, 0) # Dark green
    elif token_type in Token.String:
        return rgb(170, 85, 0) # Brown
    elif token_type in Token.Comment:
        return rgb(128, 128, 128) # Grey
    elif token_type in Token.Operator:
        return rgb(100, 100, 100) # Dark grey
    else:
        return rgb(0, 0, 0) # Black default

def get_drive_folder_id(drive_service, folder_name="Adaptive Learning Assistant Notes"):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    if not items:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = drive_service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    return items[0].get('id')


def _connect_sqlite() -> sqlite3.Connection:
    import sqlite3
    conn = sqlite3.connect(SQLITE_DB_PATH, timeout=30, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass
    return conn


def _clean_google_export_text(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()


def _google_doc_line_ranges(text: str) -> list[dict]:
    ranges = []
    index = 1
    for line in text.splitlines(keepends=True):
        line_without_newline = line.rstrip("\n")
        start = index
        end = index + len(line_without_newline)
        stripped = line_without_newline.strip()
        if stripped:
            ranges.append(
                {
                    "text": stripped,
                    "start": start,
                    "end": end,
                    "paragraph_end": index + len(line),
                }
            )
        index += len(line)
    return ranges


def _google_doc_formatting_requests(text: str) -> list[dict]:
    requests = []
    lines = _google_doc_line_ranges(text)
    
    for position, line in enumerate(lines):
        line_text = line["text"]
        # Skip empty lines for paragraph styling but keep them for indices
        if not line_text.strip() and line["end"] <= line["start"]:
            continue

        paragraph_range = {"startIndex": line["start"], "endIndex": max(line["start"] + 1, line["paragraph_end"])}
        text_range = {"startIndex": line["start"], "endIndex": line["end"]}

        # 1. Paragraph-level formatting (Headings and Bullets)
        if position == 0 and not line_text.startswith("#"):
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": paragraph_range,
                        "paragraphStyle": {"namedStyleType": "TITLE", "spaceBelow": {"magnitude": 12, "unit": "PT"}},
                        "fields": "namedStyleType,spaceBelow",
                    }
                }
            )
        elif line_text.startswith("# "):
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": paragraph_range,
                        "paragraphStyle": {"namedStyleType": "HEADING_1", "spaceAbove": {"magnitude": 14, "unit": "PT"}},
                        "fields": "namedStyleType,spaceAbove",
                    }
                }
            )
        elif line_text.startswith("## "):
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": paragraph_range,
                        "paragraphStyle": {"namedStyleType": "HEADING_2", "spaceAbove": {"magnitude": 12, "unit": "PT"}},
                        "fields": "namedStyleType,spaceAbove",
                    }
                }
            )
        elif line_text.startswith("### "):
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": paragraph_range,
                        "paragraphStyle": {"namedStyleType": "HEADING_3", "spaceAbove": {"magnitude": 10, "unit": "PT"}},
                        "fields": "namedStyleType,spaceAbove",
                    }
                }
            )
        elif line_text in {"Prompt", "Tutor response", "Earlier context", "Notes", "Focus", "Summary"}:
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": paragraph_range,
                        "paragraphStyle": {"namedStyleType": "HEADING_2", "spaceAbove": {"magnitude": 10, "unit": "PT"}},
                        "fields": "namedStyleType,spaceAbove",
                    }
                }
            )
        elif line_text.startswith("- ") or line_text.startswith("* "):
            requests.append(
                {
                    "createParagraphBullets": {
                        "range": paragraph_range,
                        "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                    }
                }
            )
        
        # 2. Line-specific character formatting (Bold/Italic/Labels)
        if line_text.startswith("You:") or line_text.startswith("ArkAI:"):
            colon_index = line_text.find(":")
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {"startIndex": line["start"], "endIndex": line["start"] + colon_index + 1},
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                }
            )

        # Handle Markdown Bold **text**
        bold_matches = re.finditer(r"\*\*(.*?)\*\*", line_text)
        for match in bold_matches:
            start_off, end_off = match.span()
            requests.append({
                "updateTextStyle": {
                    "range": {
                        "startIndex": line["start"] + start_off,
                        "endIndex": line["start"] + end_off
                    },
                    "textStyle": {"bold": True},
                    "fields": "bold"
                }
            })

        # Handle Markdown Italic *text* (avoiding double-counting bold)
        italic_matches = re.finditer(r"(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)", line_text)
        for match in italic_matches:
            start_off, end_off = match.span()
            requests.append({
                "updateTextStyle": {
                    "range": {
                        "startIndex": line["start"] + start_off,
                        "endIndex": line["start"] + end_off
                    },
                    "textStyle": {"italic": True},
                    "fields": "italic"
                }
            })

        # General paragraph spacing
        if line["end"] > line["start"]:
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": text_range,
                        "paragraphStyle": {
                            "lineSpacing": 115,
                            "spaceBelow": {"magnitude": 6, "unit": "PT"},
                        },
                        "fields": "lineSpacing,spaceBelow",
                    }
                }
            )
    return requests

@mcp.tool()
def save_google_doc_note(user_id: str, title: str, note_text: str, code_snippet: str = "", language: str = "") -> dict:
    """Saves a note and optionally syntax-formatted code snippet to a new Google Doc.
    Args:
        title: Title of the document.
        note_text: The main text of the note.
        code_snippet: The raw code snippet to include and format.
        language: The programming language of the code (e.g. 'python', 'java').
    """
    creds = get_google_credentials(user_id)
    if isinstance(creds, dict):
        return creds
    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    # 1. Ensure folder exists
    folder_id = get_drive_folder_id(drive_service)
    
    # 2. Create document & move it
    doc = docs_service.documents().create(body={'title': title}).execute()
    document_id = doc.get('documentId')
    
    drive_file = drive_service.files().get(fileId=document_id, fields='parents').execute()
    previous_parents = ",".join(drive_file.get('parents', []))
    drive_service.files().update(
        fileId=document_id,
        addParents=folder_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()
    
    # 3. Insert content and apply readable document styling.
    requests = []
    cleaned_note_text = _clean_google_export_text(note_text)
    full_text = (cleaned_note_text or "No note content was provided.") + "\n\n"
    current_index = 1
    
    requests.append({
        'insertText': {
            'location': {'index': current_index},
            'text': full_text
        }
    })
    current_index += len(full_text)
    requests.extend(_google_doc_formatting_requests(full_text))
    
    if code_snippet:
        try:
            if language:
                lexer = get_lexer_by_name(language)
            else:
                lexer = guess_lexer(code_snippet)
        except:
            lexer = get_lexer_by_name('text')
            
        code_tokens = list(lex(code_snippet, lexer))
        
        code_start_index = current_index
        code_str = ""
        for ttype, value in code_tokens:
            code_str += value
            
        requests.append({
            'insertText': {
                'location': {'index': current_index},
                'text': code_str + "\n"
            }
        })
        
        requests.append({
            'updateParagraphStyle': {
                'range': {
                    'startIndex': code_start_index,
                    'endIndex': code_start_index + len(code_str)
                },
                'paragraphStyle': {
                    'shading': {
                        'backgroundColor': {
                            'color': {'rgbColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95}}
                        }
                    }
                },
                'fields': 'shading'
            }
        })
        
        idx = code_start_index
        for ttype, value in code_tokens:
            val_len = len(value)
            if val_len == 0:
                continue
                
            color = pygments_token_to_docs_color(ttype)
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': idx,
                        'endIndex': idx + val_len
                    },
                    'textStyle': {
                        'foregroundColor': color,
                        'weightedFontFamily': {
                            'fontFamily': 'Consolas'
                        }
                    },
                    'fields': 'foregroundColor, weightedFontFamily'
                }
            })
            idx += val_len
            
    if requests:
        docs_service.documents().batchUpdate(documentId=document_id, body={'requests': requests}).execute()
        
    return {
        "status": "success",
        "message": f"Note saved to Google Docs in folder 'Adaptive Learning Assistant Notes'",
        "doc_id": document_id
    }

@mcp.tool()
def save_text_file_to_drive(user_id: str, title: str, content: str) -> dict:
    """Saves readable Markdown content as a file in the ArkAI Google Drive folder."""
    creds = get_google_credentials(user_id)
    if isinstance(creds, dict):
        return creds
    drive_service = build('drive', 'v3', credentials=creds)
    folder_id = get_drive_folder_id(drive_service)
    safe_title = str(title or "ArkAI Tutor Notes").strip() or "ArkAI Tutor Notes"
    if not safe_title.lower().endswith((".md", ".txt")):
        safe_title = f"{safe_title}.md"
    media = MediaInMemoryUpload(
        _clean_google_export_text(content or "No tutor content was available to save yet.").encode("utf-8"),
        mimetype="text/markdown",
        resumable=False,
    )
    file_metadata = {
        "name": safe_title,
        "parents": [folder_id],
        "mimeType": "text/markdown",
    }
    result = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink, name",
    ).execute()
    return {
        "status": "success",
        "message": "Saved this Tutor chat to Google Drive.",
        "file_id": result.get("id"),
        "file_name": result.get("name"),
        "web_view_link": result.get("webViewLink"),
    }

@mcp.tool()
def create_study_task(user_id: str, task_title: str, due_day: str = None, notes: str = "") -> dict:
    """Creates a task on the user's primary Google Tasks list.
    Args:
        user_id: string
        task_title: title of the task
        due_day: Optional due date in YYYY-MM-DD or RFC3339 format
        notes: Optional notes to attach to the task
    """
    creds = get_google_credentials(user_id)
    if isinstance(creds, dict):
        return creds
    service = build('tasks', 'v1', credentials=creds)
    
    task_body = {
        'title': task_title,
        'notes': str(notes or f'Created by Adaptive Learning Assistant (for user {user_id})')[:8000]
    }
    if due_day:
        if 'T' not in due_day and len(due_day) == 10:
            due_day = f"{due_day}T00:00:00.000Z"
        task_body['due'] = due_day

    result = service.tasks().insert(tasklist='@default', body=task_body).execute()
    
    return {
        "status": "success",
        "message": f"Task created in Google Tasks",
        "task_title": task_title,
        "task_id": result.get('id')
    }

@mcp.tool()
def create_roadmap_tasks(user_id: str, include_due_dates: bool = False) -> dict:
    """Creates Google Tasks from the learner's active roadmap."""
    roadmap_result = get_roadmap(user_id)
    if roadmap_result.get("status") != "success":
        return roadmap_result

    created = []
    for phase in roadmap_result["roadmap"].get("phases", []):
        for session in phase.get("sessions", []):
            if session.get("status") == "completed":
                continue
            due_day = session.get("due_date") if include_due_dates else None
            notes = "\n".join(
                part
                for part in (
                    "Created from ArkAI roadmap.",
                    f"Focus: {session.get('focus')}" if session.get("focus") else "",
                    f"Phase goal: {phase.get('goal')}" if phase.get("goal") else "",
                )
                if part
            )
            task_result = create_study_task(
                user_id=user_id,
                task_title=f"{phase.get('title')}: {session.get('title')}",
                due_day=due_day,
                notes=notes,
            )
            if task_result.get("status") == "success":
                created.append(
                    {
                        "task_title": task_result.get("task_title"),
                        "task_id": task_result.get("task_id"),
                    }
                )

    return {
        "status": "success",
        "created_tasks": created,
        "message": f"Created {len(created)} roadmap task(s) in Google Tasks.",
    }

@mcp.tool()
def list_study_tasks(user_id: str) -> dict:
    creds = get_google_credentials(user_id)
    if isinstance(creds, dict):
        return creds
    service = build('tasks', 'v1', credentials=creds)
    
    results = service.tasks().list(tasklist='@default', maxResults=10, showCompleted=False).execute()
    items = results.get('items', [])
    
    tasks = []
    for item in items:
        tasks.append({
            "id": item.get('id'),
            "task_title": item.get('title'),
            "due": item.get('due'),
            "status": item.get('status')
        })

    return {"status": "success", "tasks": tasks}

@mcp.tool()
def create_calendar_event(user_id: str, event_title: str, start_time_iso: str, end_time_iso: str, description: str = "") -> dict:
    """Creates an event on the user's primary Google Calendar.
    Args:
        event_title: The title of the event
        start_time_iso: Start time in ISO 8601 format with timezone (e.g. 2026-04-05T10:00:00+07:00 or Z)
        end_time_iso: End time in ISO 8601 format with timezone (e.g. 2026-04-05T11:00:00+07:00 or Z)
        description: Optional description for the event.
    """
    creds = get_google_credentials(user_id)
    if isinstance(creds, dict):
        return creds
    service = build('calendar', 'v3', credentials=creds)
    event = {
      'summary': event_title,
      'description': description,
      'start': {
        'dateTime': start_time_iso,
      },
      'end': {
        'dateTime': end_time_iso,
      },
    }
    event_result = service.events().insert(calendarId='primary', body=event).execute()
    return {
        "status": "success",
        "message": f"Event created: {event_result.get('htmlLink')}"
    }

@mcp.tool()
def save_weekly_report_doc(user_id: str, title: str = "") -> dict:
    """Generates the learner's weekly report and saves it to Google Docs."""
    report = generate_weekly_report(user_id)
    if report.get("status") != "success":
        return report
    report_title = title or report.get("title") or "ARKAIS Weekly Learning Report"
    return save_google_doc_note(
        user_id=user_id,
        title=report_title,
        note_text=report.get("note_text", ""),
    )

@mcp.tool()
def save_assessment_doc(user_id: str, assessment_id: str, title: str = "") -> dict:
    """Saves a mock test or assessment to Google Docs."""
    from learner_state import _get_assessment_record
    record = _get_assessment_record(user_id, assessment_id)
    if not record:
        return {"status": "error", "message": "Assessment not found."}
    
    report_title = title or f"ARKAIS Mock Test: {record.get('topic', 'General')}"
    
    lines = []
    lines.append(report_title)
    lines.append(f"Topic: {record.get('topic', 'General learning')}")
    lines.append(f"Level: {record.get('level', 'beginner')}")
    if record.get('goal'):
        lines.append(f"Goal: {record.get('goal')}")
    lines.append("")
    
    for i, question in enumerate(record.get("questions", [])):
        q_type = question.get("question_type", "multiple_choice").replace("_", " ")
        lines.append(f"Question {i + 1} ({q_type})")
        lines.append(question.get("prompt", ""))
        
        if question.get("question_type", "multiple_choice") == "multiple_choice":
            options = question.get("options", {})
            for key in ["A", "B", "C", "D"]:
                if key in options:
                    lines.append(f"{key}) {options[key]}")
        lines.append("")
        
    return save_google_doc_note(
        user_id=user_id,
        title=report_title,
        note_text="\n".join(lines),
    )

@mcp.tool()
def save_note(user_id: str, topic: str, note: str) -> dict:
    return save_study_note(user_id=user_id, topic=topic, note=note)

@mcp.tool()
def list_notes(user_id: str) -> dict:
    return list_study_notes(user_id=user_id, limit=10)

@mcp.tool()
def get_current_time(timezone_name: str = None) -> dict:
    """Gets the user's current local time and timezone."""

    try:
        if timezone_name:
            tz = zoneinfo.ZoneInfo(timezone_name)
        else:
            # Default fallback → Asia/Bangkok (Thailand)
            tz = zoneinfo.ZoneInfo("Asia/Bangkok")

        now = datetime.datetime.now(tz)

    except Exception:
        # Final fallback (safe default)
        now = datetime.datetime.now(datetime.timezone.utc)

    tz_name = now.tzname()
    offset = now.strftime('%z')
    offset_formatted = f"{offset[:3]}:{offset[3:]}" if offset else ""

    return {
        "status": "success",
        "current_time_iso": now.isoformat(),
        "timezone_name": tz_name,
        "utc_offset": offset_formatted
    }

if __name__ == "__main__":
    mcp.run()
