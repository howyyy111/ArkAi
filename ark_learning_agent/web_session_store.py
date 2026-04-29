import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import json
import os

try:
    from .learner_state import get_firestore_client
except ImportError:
    from learner_state import get_firestore_client


BASE_DIR = Path(__file__).resolve().parent
SQLITE_DB_PATH = BASE_DIR / "web_sessions.db"
BROWSER_CLIENTS_COLLECTION = "browser_clients"
CHAT_SESSIONS_COLLECTION = "chat_sessions"
BROWSER_CLIENT_RETENTION_DAYS = max(1, int((os.environ.get("ARKAIS_BROWSER_CLIENT_RETENTION_DAYS") or "30").strip()))
CHAT_SESSION_RETENTION_DAYS = max(1, int((os.environ.get("ARKAIS_CHAT_SESSION_RETENTION_DAYS") or "90").strip()))
CHAT_MESSAGE_RETENTION_DAYS = max(1, int((os.environ.get("ARKAIS_CHAT_MESSAGE_RETENTION_DAYS") or "90").strip()))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expiry_iso(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _connect() -> sqlite3.Connection:
    init_web_session_sqlite()
    return sqlite3.connect(SQLITE_DB_PATH, timeout=30)


def init_web_session_sqlite() -> None:
    conn = sqlite3.connect(SQLITE_DB_PATH, timeout=30)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS browser_clients (
            client_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            is_authenticated INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            session_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            expires_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            message_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            author TEXT,
            content TEXT NOT NULL,
            metadata_json TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT
        )
        """
    )

    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_client_id ON chat_sessions(client_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id)"
    )
    cur.execute("PRAGMA table_info(browser_clients)")
    if "expires_at" not in {row[1] for row in cur.fetchall()}:
        cur.execute("ALTER TABLE browser_clients ADD COLUMN expires_at TEXT")
    cur.execute("PRAGMA table_info(chat_sessions)")
    if "expires_at" not in {row[1] for row in cur.fetchall()}:
        cur.execute("ALTER TABLE chat_sessions ADD COLUMN expires_at TEXT")
    cur.execute("PRAGMA table_info(chat_messages)")
    if "expires_at" not in {row[1] for row in cur.fetchall()}:
        cur.execute("ALTER TABLE chat_messages ADD COLUMN expires_at TEXT")

    conn.commit()
    conn.close()


def _new_guest_user_id() -> str:
    return f"guest:{uuid.uuid4().hex}"


def _new_client_id() -> str:
    return uuid.uuid4().hex


def _new_session_id() -> str:
    return str(uuid.uuid4())


def _browser_client_doc(db, client_id: str):
    return db.collection(BROWSER_CLIENTS_COLLECTION).document(client_id)


def _user_doc(db, user_id: str):
    return db.collection("users").document(user_id)


def _user_chat_sessions_collection(db, user_id: str):
    return _user_doc(db, user_id).collection(CHAT_SESSIONS_COLLECTION)


def _chat_session_doc_for_user(db, user_id: str, session_id: str):
    return _user_chat_sessions_collection(db, user_id).document(session_id)


def _chat_messages_collection(db, user_id: str, session_id: str):
    return _chat_session_doc_for_user(db, user_id, session_id).collection("messages")


def _user_doc_payload(user_id: str, *, now: str | None = None) -> dict[str, Any]:
    normalized_user_id = str(user_id).strip()
    payload: dict[str, Any] = {
        "user_id": normalized_user_id,
        "is_anonymous": normalized_user_id.startswith("guest:"),
        "updated_at": now or _utc_now(),
    }
    if payload["is_anonymous"]:
        payload["expires_at"] = _expiry_iso(BROWSER_CLIENT_RETENTION_DAYS)
    return payload


def _firestore_browser_identity(
    client_id: str | None = None,
    authenticated_user_id: str = "",
    reset_identity: bool = False,
) -> dict[str, str | bool]:
    db = get_firestore_client()
    if not db:
        return {}

    normalized_client_id = (client_id or "").strip()
    normalized_user_id = authenticated_user_id.strip()
    now = _utc_now()

    if reset_identity or not normalized_client_id:
        normalized_client_id = _new_client_id()
        current_user_id = normalized_user_id or _new_guest_user_id()
        is_authenticated = bool(normalized_user_id)
        expires_at = "" if is_authenticated else _expiry_iso(BROWSER_CLIENT_RETENTION_DAYS)
        _browser_client_doc(db, normalized_client_id).set(
            {
                "client_id": normalized_client_id,
                "user_id": current_user_id,
                "is_authenticated": is_authenticated,
                "created_at": now,
                "updated_at": now,
                "expires_at": expires_at,
            }
        )
        _user_doc(db, current_user_id).set(_user_doc_payload(current_user_id, now=now), merge=True)
        return {
            "client_id": normalized_client_id,
            "user_id": current_user_id,
            "is_authenticated": is_authenticated,
        }

    snapshot = _browser_client_doc(db, normalized_client_id).get()
    if not snapshot.exists:
        current_user_id = normalized_user_id or _new_guest_user_id()
        is_authenticated = bool(normalized_user_id)
        expires_at = "" if is_authenticated else _expiry_iso(BROWSER_CLIENT_RETENTION_DAYS)
        _browser_client_doc(db, normalized_client_id).set(
            {
                "client_id": normalized_client_id,
                "user_id": current_user_id,
                "is_authenticated": is_authenticated,
                "created_at": now,
                "updated_at": now,
                "expires_at": expires_at,
            }
        )
        _user_doc(db, current_user_id).set(_user_doc_payload(current_user_id, now=now), merge=True)
        return {
            "client_id": normalized_client_id,
            "user_id": current_user_id,
            "is_authenticated": is_authenticated,
        }

    record = snapshot.to_dict() or {}
    current_user_id = str(record.get("user_id", "")).strip() or _new_guest_user_id()
    is_authenticated = bool(record.get("is_authenticated"))

    if normalized_user_id and current_user_id != normalized_user_id:
        current_user_id = normalized_user_id
        is_authenticated = True
        _browser_client_doc(db, normalized_client_id).set(
            {
                "client_id": normalized_client_id,
                "user_id": current_user_id,
                "is_authenticated": True,
                "created_at": str(record.get("created_at") or now),
                "updated_at": now,
                "expires_at": "",
            }
        )
        _user_doc(db, current_user_id).set(_user_doc_payload(current_user_id, now=now), merge=True)
    else:
        _browser_client_doc(db, normalized_client_id).set(
            {
                "updated_at": now,
                "expires_at": "" if is_authenticated else _expiry_iso(BROWSER_CLIENT_RETENTION_DAYS),
            },
            merge=True,
        )
        _user_doc(db, current_user_id).set(_user_doc_payload(current_user_id, now=now), merge=True)

    return {
        "client_id": normalized_client_id,
        "user_id": current_user_id,
        "is_authenticated": is_authenticated,
    }


def _sqlite_browser_identity(
    client_id: str | None = None,
    authenticated_user_id: str = "",
    reset_identity: bool = False,
) -> dict[str, str | bool]:
    normalized_client_id = (client_id or "").strip()
    normalized_user_id = authenticated_user_id.strip()
    now = _utc_now()

    with _connect() as conn:
        cur = conn.cursor()

        if reset_identity or not normalized_client_id:
            normalized_client_id = _new_client_id()
            current_user_id = normalized_user_id or _new_guest_user_id()
            is_authenticated = 1 if normalized_user_id else 0
            expires_at = None if is_authenticated else _expiry_iso(BROWSER_CLIENT_RETENTION_DAYS)
            cur.execute(
                """
                INSERT OR REPLACE INTO browser_clients
                (client_id, user_id, is_authenticated, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (normalized_client_id, current_user_id, is_authenticated, now, now, expires_at),
            )
            return {
                "client_id": normalized_client_id,
                "user_id": current_user_id,
                "is_authenticated": bool(is_authenticated),
            }

        cur.execute(
            """
            SELECT user_id, is_authenticated
            FROM browser_clients
            WHERE client_id = ?
            """,
            (normalized_client_id,),
        )
        row = cur.fetchone()

        if not row:
            current_user_id = normalized_user_id or _new_guest_user_id()
            is_authenticated = 1 if normalized_user_id else 0
            expires_at = None if is_authenticated else _expiry_iso(BROWSER_CLIENT_RETENTION_DAYS)
            cur.execute(
                """
                INSERT INTO browser_clients
                (client_id, user_id, is_authenticated, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (normalized_client_id, current_user_id, is_authenticated, now, now, expires_at),
            )
            return {
                "client_id": normalized_client_id,
                "user_id": current_user_id,
                "is_authenticated": bool(is_authenticated),
            }

        current_user_id = str(row[0]).strip()
        is_authenticated = bool(row[1])

        if normalized_user_id and current_user_id != normalized_user_id:
            current_user_id = normalized_user_id
            is_authenticated = True
            cur.execute(
                """
                UPDATE browser_clients
                SET user_id = ?, is_authenticated = 1, updated_at = ?, expires_at = NULL
                WHERE client_id = ?
                """,
                (current_user_id, now, normalized_client_id),
            )
        else:
            cur.execute(
                "UPDATE browser_clients SET updated_at = ?, expires_at = ? WHERE client_id = ?",
                (now, None if is_authenticated else _expiry_iso(BROWSER_CLIENT_RETENTION_DAYS), normalized_client_id),
            )

        return {
            "client_id": normalized_client_id,
            "user_id": current_user_id,
            "is_authenticated": is_authenticated,
        }


def get_or_create_browser_identity(
    client_id: str | None = None,
    authenticated_user_id: str = "",
    reset_identity: bool = False,
) -> dict[str, str | bool]:
    return _firestore_browser_identity(
        client_id=client_id,
        authenticated_user_id=authenticated_user_id,
        reset_identity=reset_identity,
    ) or _sqlite_browser_identity(
        client_id=client_id,
        authenticated_user_id=authenticated_user_id,
        reset_identity=reset_identity,
    )


def _firestore_chat_session(
    client_id: str,
    user_id: str,
    session_id: str | None = None,
    reset_session: bool = False,
) -> dict[str, str]:
    db = get_firestore_client()
    if not db:
        return {}

    normalized_client_id = client_id.strip()
    normalized_user_id = user_id.strip()
    normalized_session_id = (session_id or "").strip()
    now = _utc_now()

    if not reset_session and normalized_session_id:
        snapshot = _chat_session_doc_for_user(db, normalized_user_id, normalized_session_id).get()
        if snapshot.exists:
            record = snapshot.to_dict() or {}
            if (
                str(record.get("client_id", "")).strip() == normalized_client_id
                and str(record.get("user_id", "")).strip() == normalized_user_id
            ):
                _chat_session_doc_for_user(db, normalized_user_id, normalized_session_id).set(
                    {
                        "updated_at": now,
                        "expires_at": _expiry_iso(CHAT_SESSION_RETENTION_DAYS),
                    },
                    merge=True,
                )
                return {
                    "session_id": normalized_session_id,
                    "client_id": normalized_client_id,
                    "user_id": normalized_user_id,
                }

    normalized_session_id = _new_session_id()
    _user_doc(db, normalized_user_id).set(
        _user_doc_payload(normalized_user_id, now=now),
        merge=True,
    )
    _chat_session_doc_for_user(db, normalized_user_id, normalized_session_id).set(
        {
            "session_id": normalized_session_id,
            "client_id": normalized_client_id,
            "user_id": normalized_user_id,
            "created_at": now,
            "updated_at": now,
            "expires_at": _expiry_iso(CHAT_SESSION_RETENTION_DAYS),
        }
    )
    return {
        "session_id": normalized_session_id,
        "client_id": normalized_client_id,
        "user_id": normalized_user_id,
    }


def _sqlite_chat_session(
    client_id: str,
    user_id: str,
    session_id: str | None = None,
    reset_session: bool = False,
) -> dict[str, str]:
    normalized_client_id = client_id.strip()
    normalized_user_id = user_id.strip()
    normalized_session_id = (session_id or "").strip()
    now = _utc_now()

    with _connect() as conn:
        cur = conn.cursor()

        if not reset_session and normalized_session_id:
            cur.execute(
                """
                SELECT client_id, user_id
                FROM chat_sessions
                WHERE session_id = ?
                """,
                (normalized_session_id,),
            )
            row = cur.fetchone()
            if row and row[0] == normalized_client_id and row[1] == normalized_user_id:
                cur.execute(
                    "UPDATE chat_sessions SET updated_at = ?, expires_at = ? WHERE session_id = ?",
                    (now, _expiry_iso(CHAT_SESSION_RETENTION_DAYS), normalized_session_id),
                )
                return {
                    "session_id": normalized_session_id,
                    "client_id": normalized_client_id,
                    "user_id": normalized_user_id,
                }

        normalized_session_id = _new_session_id()
        cur.execute(
            """
            INSERT INTO chat_sessions
            (session_id, client_id, user_id, created_at, updated_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                normalized_session_id,
                normalized_client_id,
                normalized_user_id,
                now,
                now,
                _expiry_iso(CHAT_SESSION_RETENTION_DAYS),
            ),
        )
        return {
            "session_id": normalized_session_id,
            "client_id": normalized_client_id,
            "user_id": normalized_user_id,
        }


def get_or_create_chat_session(
    client_id: str,
    user_id: str,
    session_id: str | None = None,
    reset_session: bool = False,
) -> dict[str, str]:
    return _firestore_chat_session(
        client_id=client_id,
        user_id=user_id,
        session_id=session_id,
        reset_session=reset_session,
    ) or _sqlite_chat_session(
        client_id=client_id,
        user_id=user_id,
        session_id=session_id,
        reset_session=reset_session,
    )


def append_chat_message(
    user_id: str,
    session_id: str,
    role: str,
    content: str,
    *,
    author: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    normalized_user_id = str(user_id or "").strip()
    normalized_session_id = str(session_id or "").strip()
    normalized_role = str(role or "").strip() or "message"
    text = str(content or "").strip()
    if not normalized_user_id or not normalized_session_id or not text:
        return

    now = _utc_now()
    payload = {
        "message_id": str(uuid.uuid4()),
        "role": normalized_role,
        "author": str(author or normalized_role).strip() or normalized_role,
        "content": text,
        "created_at": now,
        "expires_at": _expiry_iso(CHAT_MESSAGE_RETENTION_DAYS),
        "metadata": metadata or {},
    }

    db = get_firestore_client()
    if db:
        _chat_messages_collection(db, normalized_user_id, normalized_session_id).document(payload["message_id"]).set(payload)
        _chat_session_doc_for_user(db, normalized_user_id, normalized_session_id).set(
            {
                "last_message_at": now,
                "updated_at": now,
            },
            merge=True,
        )
        _user_doc(db, normalized_user_id).set(
            _user_doc_payload(normalized_user_id, now=now),
            merge=True,
        )
        return

    with _connect() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO chat_messages
            (message_id, session_id, user_id, role, author, content, metadata_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["message_id"],
                normalized_session_id,
                normalized_user_id,
                payload["role"],
                payload["author"],
                payload["content"],
                json.dumps(payload["metadata"]),
                now,
                payload["expires_at"],
            ),
        )
        cur.execute(
            "UPDATE chat_sessions SET updated_at = ?, expires_at = ? WHERE session_id = ?",
            (now, _expiry_iso(CHAT_SESSION_RETENTION_DAYS), normalized_session_id),
        )
