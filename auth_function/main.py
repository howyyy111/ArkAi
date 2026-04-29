import functions_framework
import json
import os
from pathlib import Path

from google_auth_oauthlib.flow import Flow
import firebase_admin
from firebase_admin import firestore
from google.cloud import firestore as google_cloud_firestore


def _firebase_project_id() -> str:
    return (
        os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or os.environ.get("FIREBASE_PROJECT_ID")
        or ""
    ).strip()


def _initialize_firestore():
    project_id = _firebase_project_id()
    if project_id:
        firebase_admin.initialize_app(options={"projectId": project_id})
    else:
        firebase_admin.initialize_app()

    database_id = (os.environ.get("FIRESTORE_DATABASE") or "").strip()
    if database_id:
        client = google_cloud_firestore.Client(project=project_id or None, database=database_id)
    else:
        client = firestore.client()

    if not bool(os.environ.get("K_SERVICE")):
        client.collection("test").document("test").get()
    return client


try:
    db = _initialize_firestore()
except Exception as exc:
    print(f"Firebase Admin initialization failed: {exc}", flush=True)
    db = None

SCOPES = [
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file'
]


_SECRETS_PATH = Path(__file__).resolve().parent / "credentials.json"


def _production_https_redirect_uri_from_secrets(path: Path) -> str | None:
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


def _callback_redirect_uri(request):
    """Must exactly match redirect_uri from the authorize request (see AUTH_CALLBACK_URL / credentials.json)."""
    from_file = _production_https_redirect_uri_from_secrets(_SECRETS_PATH)
    for key in ("OAUTH_REDIRECT_URI", "AUTH_CALLBACK_URL"):
        u = (os.environ.get(key) or "").strip()
        if u and (not from_file or u == from_file):
            return u
    if from_file:
        return from_file
    merged = f"https://{request.host}{request.path}"
    return merged.rstrip("/")


def _normalize_oauth_user_id(user_id: str) -> str:
    return str(user_id or "").strip().lower()


def _user_google_oauth_doc(user_id: str):
    return (
        db.collection("users")
        .document(_normalize_oauth_user_id(user_id))
        .collection("integrations")
        .document("google_oauth")
    )

def _resolve_oauth_state_user_id(state: str) -> str:
    normalized_state = str(state or "").strip()
    if not normalized_state:
        return ""

    state_doc = db.collection("google_oauth_states").document(normalized_state)
    snapshot = state_doc.get()
    if snapshot.exists:
        payload = snapshot.to_dict() or {}
        user_id = _normalize_oauth_user_id(payload.get("user_id", ""))
        if user_id:
            state_doc.set(
                {
                    "status": "used",
                    "used_at": firestore.SERVER_TIMESTAMP,
                },
                merge=True,
            )
            return user_id

    if os.environ.get("ALLOW_LEGACY_OAUTH_STATE") == "1":
        return _normalize_oauth_user_id(normalized_state)
    return ""


@functions_framework.http
def auth_callback(request):
    """HTTP Cloud Function for handling Google OAuth callback."""
    if not db:
        return "Internal Error: Firebase not initialized in Cloud Function.", 500
        
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        return "Missing 'code' or 'state' parameters from Google.", 400
        
    username = _resolve_oauth_state_user_id(state)
    if not username:
        return "Invalid or expired OAuth state. Return to ArkAI and connect Google saves again.", 400

    redirect_uri = _callback_redirect_uri(request)

    try:
        # Must match the MCP server: no PKCE, since code exchange happens on this host
        # without the original Flow's code_verifier.
        flow = Flow.from_client_secrets_file(
            'credentials.json',
            scopes=SCOPES,
            state=state,
            autogenerate_code_verifier=False,
        )
        flow.redirect_uri = redirect_uri
        
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        creds_dict = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
            "provider": "google_oauth",
        }
        db.collection("users").document(username).set(
            {
                "user_id": username,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )
        _user_google_oauth_doc(username).set(
            {
                **creds_dict,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
        )
        
        return f"<h1>Success!</h1><p>Tokens saved securely in Firebase for user: <b>{username}</b></p><br><p>You can close this tab and return to the chat, tell the agent you have authorized it, and repeat your command!</p>"
        
    except Exception as e:
        return f"<h3>OAuth Flow Failed:</h3><pre>{str(e)}</pre>", 500
