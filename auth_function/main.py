import functions_framework
import json
import os
from pathlib import Path

from flask import request
from google_auth_oauthlib.flow import Flow
import firebase_admin
from firebase_admin import firestore

try:
    firebase_admin.initialize_app()
    db = firestore.client()
    if not bool(os.environ.get("K_SERVICE")):
        db.collection("test").document("test").get()
except Exception:
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
    for key in ("OAUTH_REDIRECT_URI", "AUTH_CALLBACK_URL"):
        u = (os.environ.get(key) or "").strip()
        if u:
            return u
    from_file = _production_https_redirect_uri_from_secrets(_SECRETS_PATH)
    if from_file:
        return from_file
    merged = f"https://{request.host}{request.path}"
    return merged.rstrip("/")


@functions_framework.http
def auth_callback(request):
    """HTTP Cloud Function for handling Google OAuth callback."""
    if not db:
        return "Internal Error: Firebase not initialized in Cloud Function.", 500
        
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        return "Missing 'code' or 'state' parameters from Google.", 400
        
    username = state

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
            "scopes": creds.scopes
        }
        db.collection("user_tokens").document(username).set(creds_dict)
        
        return f"<h1>Success!</h1><p>Tokens saved securely in Firebase for user: <b>{username}</b></p><br><p>You can close this tab and return to the chat, tell the agent you have authorized it, and repeat your command!</p>"
        
    except Exception as e:
        return f"<h3>OAuth Flow Failed:</h3><pre>{str(e)}</pre>", 500
