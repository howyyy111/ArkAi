import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "learning_agent.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS learner_profiles (
        user_id TEXT PRIMARY KEY,
        topic TEXT,
        level TEXT,
        learning_style TEXT,
        available_time INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS learning_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        topic TEXT,
        activity_type TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def save_learner_profile(
    user_id: str,
    topic: str,
    level: str,
    learning_style: str,
    available_time: int
) -> dict:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    INSERT OR REPLACE INTO learner_profiles
    (user_id, topic, level, learning_style, available_time)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, topic, level, learning_style, available_time))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": f"Profile saved for user {user_id}"
    }


def get_learner_profile(user_id: str) -> dict:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    SELECT user_id, topic, level, learning_style, available_time
    FROM learner_profiles
    WHERE user_id = ?
    """, (user_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return {"status": "not_found", "message": "No learner profile found"}

    return {
        "status": "success",
        "user_id": row[0],
        "topic": row[1],
        "level": row[2],
        "learning_style": row[3],
        "available_time": row[4]
    }


def save_learning_progress(
    user_id: str,
    topic: str,
    activity_type: str,
    notes: str
) -> dict:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO learning_progress
    (user_id, topic, activity_type, notes)
    VALUES (?, ?, ?, ?)
    """, (user_id, topic, activity_type, notes))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": f"Progress saved for user {user_id}"
    }


def get_learning_history(user_id: str) -> dict:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    SELECT topic, activity_type, notes, created_at
    FROM learning_progress
    WHERE user_id = ?
    ORDER BY created_at DESC
    LIMIT 10
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "topic": row[0],
            "activity_type": row[1],
            "notes": row[2],
            "created_at": row[3]
        })

    return {
        "status": "success",
        "history": history
    }