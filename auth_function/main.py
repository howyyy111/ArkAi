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
        
        return """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Google saves connected</title>
            <style>
                body {
                    margin: 0;
                    min-height: 100vh;
                    display: grid;
                    place-items: center;
                    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                    color: #111827;
                    background: #f8fafc;
                }
                main {
                    width: min(440px, calc(100% - 32px));
                    border: 1px solid #e5e7eb;
                    border-radius: 20px;
                    padding: 28px;
                    background: #ffffff;
                    box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
                }
                h1 { margin: 0 0 10px; font-size: 1.45rem; }
                p { margin: 0; color: #4b5563; line-height: 1.55; }
            </style>
        </head>
        <body>
            <main>
                <h1>Google saves connected</h1>
                <p>You can return to ArkAI now. This window will close automatically if your browser allows it.</p>
            </main>
            <script>
                if (window.opener && !window.opener.closed) {
                    window.opener.postMessage({ type: "arkai:google-oauth", status: "success" }, "*");
                    window.setTimeout(() => window.close(), 1200);
                }
            </script>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"<h3>OAuth Flow Failed:</h3><pre>{str(e)}</pre>", 500
