import sqlite3
import os
from dotenv import load_dotenv
import datetime
import threading
import time
import requests
import json
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build

import firebase_admin
from firebase_admin import firestore

mcp = FastMCP("productivity-tools")

BASE_DIR = Path(__file__).resolve().parent
# Load repo root .env first, then package .env (package wins on duplicate keys).
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env", override=True)

def _running_on_cloud_run() -> bool:
    """Cloud Run sets K_SERVICE; Cloud Functions Gen2 on Cloud Run may set FUNCTION_TARGET."""
    return bool(os.environ.get("K_SERVICE"))


try:
    _gcp_project = (os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT") or "").strip()
    if _gcp_project:
        firebase_admin.initialize_app(options={"projectId": _gcp_project})
    else:
        firebase_admin.initialize_app()
    db = firestore.client()
    if not _running_on_cloud_run():
        # Validate that firestore actually exists in the project by testing a read
        db.collection("test").document("test").get()
except Exception:
    db = None

from pygments import lex
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.token import Token

DB_PATH = BASE_DIR / "learning_agent.db"
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"
USER_GOOGLE_TOKENS_DIR = BASE_DIR / "user_google_tokens"

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
    env_uri = (os.environ.get("AUTH_CALLBACK_URL") or "").strip()
    from_file = _production_https_redirect_uri_from_secrets(CREDENTIALS_PATH)
    if env_uri:
        return env_uri
    if from_file:
        return from_file
    return ""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS study_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        topic TEXT,
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def _safe_user_id_for_path(user_id: str) -> str:
    return "".join(c if c.isalnum() or c in "@._-" else "_" for c in str(user_id).strip())[:200]

def _user_google_token_path(user_id: str) -> Path:
    USER_GOOGLE_TOKENS_DIR.mkdir(parents=True, exist_ok=True)
    return USER_GOOGLE_TOKENS_DIR / f"{_safe_user_id_for_path(user_id)}.json"

def _load_google_credentials_from_disk(user_id: str):
    path = _user_google_token_path(user_id)
    if path.is_file():
        return Credentials.from_authorized_user_file(str(path), SCOPES)
    if os.environ.get("ALLOW_LEGACY_SHARED_TOKEN") == "1" and TOKEN_PATH.is_file():
        return Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    return None

def _persist_google_credentials(user_id: str, creds: Credentials) -> None:
    payload = json.loads(creds.to_json())
    if db:
        db.collection("user_tokens").document(user_id).set(payload)
    else:
        path = _user_google_token_path(user_id)
        path.write_text(creds.to_json(), encoding="utf-8")

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

def get_google_credentials(user_id):
    if not user_id or str(user_id).strip() == "":
        return {
            "status": "error",
            "message": "CRITICAL RULE VIOLATION: You MUST ask the user for their username or Gmail address first! You passed an empty user_id string to the tool."
        }

    creds = None
    if db:
        doc = db.collection("user_tokens").document(user_id).get()
        if doc.exists:
            creds = Credentials.from_authorized_user_info(doc.to_dict(), SCOPES)
    else:
        creds = _load_google_credentials_from_disk(user_id)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                if db:
                    db.collection("user_tokens").document(user_id).update({"token": creds.token})
                else:
                    _persist_google_credentials(user_id, creds)
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

        auth_url = _cloud_oauth_redirect_uri()

        # Local dev without Firestore: loopback browser login. On Cloud Run we always use hosted redirect + Firestore.
        if not db and not _running_on_cloud_run():
            # Bypass local server to always provide the sign-in link via the tool response!
            pass

        if not auth_url:
            # Fallback to the cloud function if AUTH_CALLBACK_URL is missing
            auth_url = "https://us-central1-arkai-492511.cloudfunctions.net/auth_function"

        # Load client config directly from credentials.json
        import json
        with open(CREDENTIALS_PATH, "r") as f:
            client_config = json.load(f)

        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            state=user_id,
            autogenerate_code_verifier=False,
        )
        flow.redirect_uri = auth_url  # must match Cloud Function OAUTH_REDIRECT_URI / Console entry
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            prompt=_google_oauth_prompt(),
        )

        oauth_cid = flow.client_config.get("client_id", "")
        oauth_proj = flow.client_config.get("project_id", "")

        return {
            "status": "auth_required",
            "authorization_url": authorization_url,
            "oauth_redirect_uri": auth_url,
            "oauth_client_id": oauth_cid,
            "google_cloud_project_id": oauth_proj,
            "message": (
                "CRITICAL INSTRUCTION FOR AI AGENT: Do NOT apologize or say sign-in is broken.\n"
                "Google intentionally blocks OAuth sign-in inside many embedded chat / in-app browsers (including some Cloud Run ADK web UIs). "
                "Clicking the link inside chat often shows a blank page or skips the Google screen.\n"
                "You MUST tell the user to COPY the URL below and PASTE it into Chrome or Safari's address bar (full browser), not only tap the chat link.\n"
                "Format for the user:\n"
                "1) Short heading: e.g. 'Google sign-in (use your desktop browser)'\n"
                "2) One line of explanation about copy-paste if the in-app link does not show Google.\n"
                "3) Put ONLY this URL on its own line inside a markdown fenced code block (``` ... ```) so they can copy it in one gesture:\n"
                f"{authorization_url}\n"
                "4) Say they should see Google's account picker and permission screen for Docs/Calendar/Tasks; after the Success page on the callback site, return to chat and ask to save again using the same user_id.\n"
                "Use the tool field `authorization_url` if you need the raw string again.\n"
                "If the user reports Google error 401 invalid_client or 'OAuth client was not found', tell them: the OAuth Web Client ID in the deployed credentials.json "
                f"(this server uses oauth_client_id={oauth_cid}, project={oauth_proj}) must exist in Google Cloud Console under that project (APIs & Services → Credentials). "
                "They should download a fresh client JSON, replace credentials.json in both the ADK/MCP image and the auth callback service, redeploy both, and ensure redirect URIs match."
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
    
    # 3. Format requests
    requests = []
    full_text = note_text + "\n\n"
    current_index = 1
    
    requests.append({
        'insertText': {
            'location': {'index': current_index},
            'text': full_text
        }
    })
    current_index += len(full_text)
    
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
def create_study_task(user_id: str, task_title: str, due_day: str = None) -> dict:
    """Creates a task on the user's primary Google Tasks list.
    Args:
        user_id: string
        task_title: title of the task
        due_day: Optional due date in YYYY-MM-DD or RFC3339 format
    """
    creds = get_google_credentials(user_id)
    if isinstance(creds, dict):
        return creds
    service = build('tasks', 'v1', credentials=creds)
    
    task_body = {
        'title': task_title,
        'notes': f'Created by Adaptive Learning Assistant (for user {user_id})'
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
def save_note(user_id: str, topic: str, note: str) -> dict:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO study_notes (user_id, topic, note)
    VALUES (?, ?, ?)
    """, (user_id, topic, note))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": f"Note saved for {user_id}",
        "topic": topic
    }

@mcp.tool()
def list_notes(user_id: str) -> dict:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    SELECT topic, note, created_at
    FROM study_notes
    WHERE user_id = ?
    ORDER BY created_at DESC
    LIMIT 10
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    notes = []
    for row in rows:
        notes.append({
            "topic": row[0],
            "note": row[1],
            "created_at": row[2]
        })

    return {"status": "success", "notes": notes}

@mcp.tool()
def get_current_time() -> dict:
    """Gets the user's current local time and timezone."""
    now = datetime.datetime.now().astimezone()
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
