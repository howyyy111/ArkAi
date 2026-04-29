#!/usr/bin/env python3

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ark_learning_agent.learner_state import get_firestore_client
from ark_learning_agent.materials import UPLOADS_DIR
from ark_learning_agent.web_session_store import (
    BROWSER_CLIENT_RETENTION_DAYS,
    CHAT_MESSAGE_RETENTION_DAYS,
    CHAT_SESSION_RETENTION_DAYS,
    SQLITE_DB_PATH,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def is_expired(value: str | None, now: datetime) -> bool:
    dt = parse_iso(value)
    return bool(dt and dt <= now)


def delete_document_tree(doc_ref, dry_run: bool) -> int:
    deleted = 0
    for subcollection in doc_ref.collections():
        for subdoc in subcollection.stream():
            deleted += delete_document_tree(subdoc.reference, dry_run)
    if dry_run:
        print(f"would_delete_doc {doc_ref.path}")
    else:
        doc_ref.delete()
        print(f"deleted_doc {doc_ref.path}")
    return deleted + 1


def cleanup_firestore(dry_run: bool) -> int:
    db = get_firestore_client()
    if not db:
        print("firestore_unavailable")
        return 0

    now = utc_now()
    deleted = 0

    for doc in db.collection("browser_clients").stream():
        data = doc.to_dict() or {}
        if is_expired(data.get("expires_at"), now):
            deleted += delete_document_tree(doc.reference, dry_run)

    for user_doc in db.collection("users").stream():
        user_data = user_doc.to_dict() or {}
        user_id = user_doc.id
        if bool(user_data.get("is_anonymous")) and is_expired(user_data.get("expires_at"), now):
            deleted += delete_document_tree(user_doc.reference, dry_run)
            continue

        for session_doc in user_doc.reference.collection("chat_sessions").stream():
            session_data = session_doc.to_dict() or {}
            if is_expired(session_data.get("expires_at"), now):
                deleted += delete_document_tree(session_doc.reference, dry_run)
                continue

            for message_doc in session_doc.reference.collection("messages").stream():
                message_data = message_doc.to_dict() or {}
                if is_expired(message_data.get("expires_at"), now):
                    if dry_run:
                        print(f"would_delete_doc {message_doc.reference.path}")
                    else:
                        message_doc.reference.delete()
                        print(f"deleted_doc {message_doc.reference.path}")
                    deleted += 1

    return deleted


def cleanup_sqlite(dry_run: bool) -> int:
    if not SQLITE_DB_PATH.exists():
        return 0

    now_iso = utc_now().isoformat()
    deleted = 0
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()

    queries = [
        ("chat_messages", "expires_at IS NOT NULL AND expires_at != '' AND expires_at <= ?", (now_iso,)),
        ("chat_sessions", "expires_at IS NOT NULL AND expires_at != '' AND expires_at <= ?", (now_iso,)),
        ("browser_clients", "expires_at IS NOT NULL AND expires_at != '' AND expires_at <= ?", (now_iso,)),
    ]

    for table, where_clause, params in queries:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {where_clause}", params)
        count = int(cur.fetchone()[0] or 0)
        deleted += count
        if count:
            if dry_run:
                print(f"would_delete_rows {table} {count}")
            else:
                cur.execute(f"DELETE FROM {table} WHERE {where_clause}", params)
                print(f"deleted_rows {table} {count}")

    if not dry_run:
        conn.commit()
    conn.close()
    return deleted


def cleanup_guest_uploads(dry_run: bool) -> int:
    if not UPLOADS_DIR.exists():
        return 0

    cutoff = utc_now() - timedelta(days=BROWSER_CLIENT_RETENTION_DAYS)
    deleted = 0
    for entry in UPLOADS_DIR.iterdir():
        if not entry.is_dir():
            continue
        if not entry.name.startswith("guest_"):
            continue
        modified = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
        if modified > cutoff:
            continue
        if dry_run:
            print(f"would_delete_dir {entry}")
        else:
            shutil.rmtree(entry, ignore_errors=True)
            print(f"deleted_dir {entry}")
        deleted += 1
    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete expired guest/session data.")
    parser.add_argument("--apply", action="store_true", help="Actually delete data instead of printing what would be removed.")
    args = parser.parse_args()

    dry_run = not args.apply
    print(
        {
            "mode": "dry_run" if dry_run else "apply",
            "browser_client_retention_days": BROWSER_CLIENT_RETENTION_DAYS,
            "chat_session_retention_days": CHAT_SESSION_RETENTION_DAYS,
            "chat_message_retention_days": CHAT_MESSAGE_RETENTION_DAYS,
        }
    )
    total = 0
    total += cleanup_firestore(dry_run)
    total += cleanup_sqlite(dry_run)
    total += cleanup_guest_uploads(dry_run)
    print({"deleted_or_matched_items": total})


if __name__ == "__main__":
    main()
