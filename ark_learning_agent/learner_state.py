import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

import firebase_admin
from firebase_admin import firestore
from google.cloud import firestore as google_cloud_firestore


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env", override=True)

SQLITE_DB_PATH = BASE_DIR / "learning_agent.db"
QUIZ_MODEL = os.environ.get("ARKAIS_ASSESSMENT_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
USERS_COLLECTION = "users"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _running_on_cloud_run() -> bool:
    return bool(os.environ.get("K_SERVICE"))


def _topic_key(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return cleaned[:80] or "general"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_firestore_client():
    if (os.environ.get("ARKAIS_FORCE_SQLITE") or "").strip() == "1":
        return None

    try:
        app = firebase_admin.get_app()
    except ValueError:
        project_id = (
            os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCLOUD_PROJECT")
            or ""
        ).strip()
        if project_id:
            app = firebase_admin.initialize_app(options={"projectId": project_id})
        else:
            app = firebase_admin.initialize_app()

    try:
        database_id = (os.environ.get("FIRESTORE_DATABASE") or "").strip()
        if database_id:
            project_id = (
                os.environ.get("GOOGLE_CLOUD_PROJECT")
                or os.environ.get("GCLOUD_PROJECT")
                or ""
            ).strip()
            db = google_cloud_firestore.Client(project=project_id or None, database=database_id)
        else:
            db = firestore.client(app=app)
        if not _running_on_cloud_run():
            db.collection("_healthcheck").document("ping").get()
        return db
    except Exception:
        return None


def _get_genai_client():
    project = (os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT") or "").strip()
    location = (os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1").strip()
    use_vertex = (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") or "").strip() == "1"

    if use_vertex and project:
        return genai.Client(vertexai=True, project=project, location=location)

    api_key = (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or "").strip()
    if api_key:
        return genai.Client(api_key=api_key)

    return None


def init_sqlite_fallback():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_profiles (
            user_id TEXT PRIMARY KEY,
            topic TEXT,
            level TEXT,
            learning_style TEXT,
            available_time INTEGER,
            goal TEXT,
            target_date TEXT,
            updated_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS learning_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            topic TEXT,
            activity_type TEXT,
            notes TEXT,
            score REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS study_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            topic TEXT,
            note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_mastery (
            user_id TEXT PRIMARY KEY,
            mastery_json TEXT,
            updated_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS assessments (
            assessment_id TEXT PRIMARY KEY,
            user_id TEXT,
            topic TEXT,
            assessment_type TEXT,
            level TEXT,
            goal TEXT,
            status TEXT,
            question_count INTEGER,
            questions_json TEXT,
            answers_json TEXT,
            result_json TEXT,
            score REAL,
            created_at TEXT,
            submitted_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_roadmaps (
            user_id TEXT PRIMARY KEY,
            roadmap_json TEXT,
            updated_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_roadmap_history (
            user_id TEXT NOT NULL,
            roadmap_id TEXT NOT NULL,
            roadmap_json TEXT,
            created_at TEXT,
            updated_at TEXT,
            PRIMARY KEY (user_id, roadmap_id)
        )
        """
    )

    def ensure_column(table_name: str, column_name: str, column_definition: str) -> None:
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cur.fetchall()}
        if column_name not in columns:
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")

    ensure_column("learner_profiles", "goal", "TEXT")
    ensure_column("learner_profiles", "target_date", "TEXT")
    ensure_column("learner_profiles", "updated_at", "TEXT")
    ensure_column("learning_progress", "score", "REAL")

    conn.commit()
    conn.close()


def _normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    topic = str(profile.get("topic", "")).strip()
    level = str(profile.get("level", "")).strip() or "beginner"
    learning_style = str(profile.get("learning_style", "")).strip() or "balanced"
    available_time = profile.get("available_time")
    goal = str(profile.get("goal", "")).strip()
    target_date = str(profile.get("target_date", "")).strip()

    try:
        available_time = int(available_time) if available_time not in ("", None) else None
    except (TypeError, ValueError):
        available_time = None

    return {
        "topic": topic,
        "level": level,
        "learning_style": learning_style,
        "available_time": available_time,
        "goal": goal,
        "target_date": target_date,
        "updated_at": _utc_now(),
    }


def _user_doc(db, user_id: str):
    return db.collection(USERS_COLLECTION).document(user_id)


def _user_profile_doc(db, user_id: str):
    return _user_doc(db, user_id).collection("profile").document("current")


def _user_mastery_doc(db, user_id: str):
    return _user_doc(db, user_id).collection("mastery").document("current")


def _user_roadmap_doc(db, user_id: str):
    return _user_doc(db, user_id).collection("roadmaps").document("current")

def _user_roadmaps_collection(db, user_id: str):
    return _user_doc(db, user_id).collection("roadmaps")


def _user_progress_collection(db, user_id: str):
    return _user_doc(db, user_id).collection("progress")


def _user_notes_collection(db, user_id: str):
    return _user_doc(db, user_id).collection("notes")


def _user_assessments_collection(db, user_id: str):
    return _user_doc(db, user_id).collection("assessments")


def _user_reports_collection(db, user_id: str):
    return _user_doc(db, user_id).collection("reports")


def _touch_user_doc(db, user_id: str, *, extra: dict[str, Any] | None = None) -> None:
    is_anonymous = str(user_id).startswith("guest:")
    payload = {
        "user_id": user_id,
        "is_anonymous": is_anonymous,
        "updated_at": _utc_now(),
    }
    if is_anonymous:
        payload["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    if extra:
        payload.update(extra)
    _user_doc(db, user_id).set(payload, merge=True)


def _default_question_set(topic: str, level: str, question_count: int) -> list[dict[str, Any]]:
    topic_label = topic or "this topic"
    base_questions = [
        {
            "prompt": f"What is the main purpose of learning {topic_label}?",
            "options": [
                "To understand its core ideas and when to apply them",
                "To memorize random terminology only",
                "To avoid using examples or practice",
                "To skip problem solving entirely",
            ],
            "correct_answer": "A",
            "explanation": f"{topic_label.title()} becomes useful when the learner understands the core idea and application.",
            "concept": "foundations",
            "difficulty": level,
        },
        {
            "prompt": f"Which study approach is strongest when starting {topic_label}?",
            "options": [
                "Short explanations, one example, and quick practice",
                "Only watching long lectures without checking understanding",
                "Ignoring mistakes and moving on",
                "Memorizing answers without understanding them",
            ],
            "correct_answer": "A",
            "explanation": "A balanced cycle of explanation, example, and practice builds understanding fastest.",
            "concept": "learning-strategy",
            "difficulty": level,
        },
        {
            "prompt": f"What usually shows that a learner is improving in {topic_label}?",
            "options": [
                "They can explain the idea and solve a small problem with it",
                "They read the title once",
                "They avoid practice questions",
                "They never check their answer",
            ],
            "correct_answer": "A",
            "explanation": "Real progress shows up in explanation and application, not just exposure.",
            "concept": "application",
            "difficulty": level,
        },
        {
            "prompt": f"If a learner gets stuck in {topic_label}, what is the best next step?",
            "options": [
                "Review the simpler concept and try one easier example",
                "Quit the topic immediately",
                "Keep repeating the same mistake without review",
                "Skip directly to advanced material",
            ],
            "correct_answer": "A",
            "explanation": "Stepping down one level and retrying is the fastest way to recover from confusion.",
            "concept": "remediation",
            "difficulty": level,
        },
        {
            "prompt": f"What is the best signal that a study roadmap for {topic_label} is working?",
            "options": [
                "Quiz performance and confidence improve over time",
                "The roadmap is long even if nothing is learned",
                "There are no checkpoints",
                "The learner never adjusts the plan",
            ],
            "correct_answer": "A",
            "explanation": "A good roadmap improves actual performance and confidence, not just activity volume.",
            "concept": "progress-check",
            "difficulty": level,
        },
    ]
    return [
        {
            **item,
            "question_id": f"q{i + 1}",
        }
        for i, item in enumerate(base_questions[:question_count])
    ]


def _generate_questions_with_model(
    topic: str,
    level: str,
    goal: str,
    available_time: int | None,
    assessment_type: str,
    question_count: int,
) -> list[dict[str, Any]]:
    client = _get_genai_client()
    if not client:
        return _default_question_set(topic, level, question_count)

    prompt = f"""
Generate a {assessment_type} assessment for a learner.

Topic: {topic or "general study skills"}
Level: {level}
Goal: {goal or "Build strong fundamentals"}
Available time per day: {available_time or "unknown"}
Question count: {question_count}

Return JSON only with this shape:
{{
  "questions": [
    {{
      "prompt": "Question text",
      "options": ["A option", "B option", "C option", "D option"],
      "correct_answer": "A",
      "explanation": "Short explanation",
      "concept": "short concept tag",
      "difficulty": "{level}"
    }}
  ]
}}

Requirements:
- Questions must be practical and diagnostic, not trivia.
- Keep wording simple and clear.
- Always return exactly 4 options per question.
- correct_answer must be one of A, B, C, D.
- Cover different sub-concepts where possible.
"""

    schema = {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "minItems": question_count,
                "maxItems": question_count,
                "items": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "options": {
                            "type": "array",
                            "minItems": 4,
                            "maxItems": 4,
                            "items": {"type": "string"},
                        },
                        "correct_answer": {"type": "string"},
                        "explanation": {"type": "string"},
                        "concept": {"type": "string"},
                        "difficulty": {"type": "string"},
                    },
                    "required": [
                        "prompt",
                        "options",
                        "correct_answer",
                        "explanation",
                        "concept",
                        "difficulty",
                    ],
                },
            }
        },
        "required": ["questions"],
    }

    try:
        response = client.models.generate_content(
            model=QUIZ_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                responseMimeType="application/json",
                responseSchema=schema,
            ),
        )
        payload = json.loads(response.text)
        questions = payload.get("questions") or []
        normalized = []
        for index, question in enumerate(questions[:question_count]):
            options = [str(option).strip() for option in (question.get("options") or [])][:4]
            if len(options) != 4:
                continue
            answer = str(question.get("correct_answer", "A")).strip().upper()[:1]
            if answer not in {"A", "B", "C", "D"}:
                answer = "A"
            normalized.append(
                {
                    "question_id": f"q{index + 1}",
                    "prompt": str(question.get("prompt", "")).strip(),
                    "options": options,
                    "correct_answer": answer,
                    "explanation": str(question.get("explanation", "")).strip(),
                    "concept": str(question.get("concept", "general")).strip() or "general",
                    "difficulty": str(question.get("difficulty", level)).strip() or level,
                }
            )
        if len(normalized) == question_count:
            return normalized
    except Exception:
        pass

    return _default_question_set(topic, level, question_count)


def _public_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    public = []
    for question in questions:
        public.append(
            {
                "question_id": question["question_id"],
                "prompt": question["prompt"],
                "question_type": question.get("question_type", "multiple_choice"),
                "options": question.get("options", []),
                "concept": question["concept"],
                "difficulty": question["difficulty"],
            }
        )
    return public


def _load_mastery(user_id: str) -> dict[str, Any]:
    db = get_firestore_client()
    if db:
        snapshot = _user_mastery_doc(db, user_id).get()
        if snapshot.exists:
            return (snapshot.to_dict() or {}).get("mastery") or {"topics": {}, "overall_score": 0.0}
        return {"topics": {}, "overall_score": 0.0}

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT mastery_json FROM learner_mastery WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row or not row[0]:
        return {"topics": {}, "overall_score": 0.0}
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return {"topics": {}, "overall_score": 0.0}


def _save_mastery(user_id: str, mastery: dict[str, Any]) -> None:
    mastery["updated_at"] = _utc_now()
    db = get_firestore_client()
    if db:
        _user_mastery_doc(db, user_id).set(
            {"mastery": mastery, "updated_at": mastery["updated_at"]},
            merge=True,
        )
        _touch_user_doc(db, user_id)
        return

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO learner_mastery (user_id, mastery_json, updated_at)
        VALUES (?, ?, ?)
        """,
        (user_id, json.dumps(mastery), mastery["updated_at"]),
    )
    conn.commit()
    conn.close()


def _score_label(score: float) -> str:
    if score >= 0.85:
        return "strong"
    if score >= 0.65:
        return "developing"
    return "needs support"


def _update_mastery_from_assessment(
    user_id: str,
    topic: str,
    assessment_type: str,
    concept_accuracy: dict[str, float],
    score: float,
) -> dict[str, Any]:
    mastery = _load_mastery(user_id)
    topics = mastery.setdefault("topics", {})
    topic_id = _topic_key(topic)
    topic_entry = topics.setdefault(
        topic_id,
        {
            "topic": topic,
            "score": 0.0,
            "label": "needs support",
            "assessments_taken": 0,
            "last_assessment_type": "",
            "updated_at": "",
            "concepts": {},
            "recent_scores": [],
        },
    )

    concepts = topic_entry.setdefault("concepts", {})
    topic_entry["topic"] = topic
    topic_entry["assessments_taken"] = int(topic_entry.get("assessments_taken", 0)) + 1
    topic_entry["last_assessment_type"] = assessment_type
    topic_entry["updated_at"] = _utc_now()

    for concept, accuracy in concept_accuracy.items():
        concept_entry = concepts.setdefault(
            concept,
            {"score": 0.0, "attempts": 0, "last_accuracy": 0.0, "updated_at": ""},
        )
        current = _safe_float(concept_entry.get("score"), 0.0)
        attempts = int(concept_entry.get("attempts", 0))
        blended = round(accuracy if attempts == 0 else (current * 0.45) + (accuracy * 0.55), 3)
        concept_entry["score"] = blended
        concept_entry["attempts"] = attempts + 1
        concept_entry["last_accuracy"] = round(accuracy, 3)
        concept_entry["updated_at"] = topic_entry["updated_at"]

    concept_scores = [entry.get("score", 0.0) for entry in concepts.values()]
    if concept_scores:
        topic_score = round(sum(concept_scores) / len(concept_scores), 3)
    else:
        topic_score = round(score, 3)
    topic_entry["score"] = topic_score
    topic_entry["label"] = _score_label(topic_score)
    recent_scores = [float(item) for item in topic_entry.get("recent_scores", [])][-4:]
    recent_scores.append(round(score, 3))
    topic_entry["recent_scores"] = recent_scores[-5:]

    topic_scores = [entry.get("score", 0.0) for entry in topics.values()]
    mastery["overall_score"] = round(sum(topic_scores) / len(topic_scores), 3) if topic_scores else 0.0
    mastery["overall_label"] = _score_label(mastery["overall_score"])
    _save_mastery(user_id, mastery)
    return mastery


def save_learner_profile(
    user_id: str,
    topic: str,
    level: str,
    learning_style: str,
    available_time: int | None,
    goal: str = "",
    target_date: str = "",
) -> dict[str, Any]:
    profile = _normalize_profile(
        {
            "topic": topic,
            "level": level,
            "learning_style": learning_style,
            "available_time": available_time,
            "goal": goal,
            "target_date": target_date,
        }
    )

    db = get_firestore_client()
    if db:
        _user_profile_doc(db, user_id).set(
            {
                "profile": profile,
                "updated_at": profile["updated_at"],
            },
            merge=True,
        )
        _touch_user_doc(db, user_id)
        return {
            "status": "success",
            "message": f"Profile saved for user {user_id}",
            "storage": "firestore",
        }

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO learner_profiles
        (user_id, topic, level, learning_style, available_time, goal, target_date, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            profile["topic"],
            profile["level"],
            profile["learning_style"],
            profile["available_time"],
            profile["goal"],
            profile["target_date"],
            profile["updated_at"],
        ),
    )
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "message": f"Profile saved for user {user_id}",
        "storage": "sqlite_fallback",
    }


def get_learner_profile(user_id: str) -> dict[str, Any]:
    db = get_firestore_client()
    if db:
        snapshot = _user_profile_doc(db, user_id).get()
        if not snapshot.exists:
            return {"status": "not_found", "message": "No learner profile found"}
        profile = (snapshot.to_dict() or {}).get("profile") or {}
        if not profile:
            return {"status": "not_found", "message": "No learner profile found"}
        return {"status": "success", "user_id": user_id, **profile}

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT topic, level, learning_style, available_time, goal, target_date, updated_at
        FROM learner_profiles
        WHERE user_id = ?
        """,
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"status": "not_found", "message": "No learner profile found"}
    return {
        "status": "success",
        "user_id": user_id,
        "topic": row[0],
        "level": row[1],
        "learning_style": row[2],
        "available_time": row[3],
        "goal": row[4],
        "target_date": row[5],
        "updated_at": row[6],
    }


def save_learning_progress(
    user_id: str,
    topic: str,
    activity_type: str,
    notes: str,
    score: float | None = None,
) -> dict[str, Any]:
    created_at = _utc_now()
    payload = {
        "topic": str(topic).strip(),
        "activity_type": str(activity_type).strip(),
        "notes": str(notes).strip(),
        "score": score,
        "created_at": created_at,
    }

    db = get_firestore_client()
    if db:
        _user_progress_collection(db, user_id).add(payload)
        _touch_user_doc(db, user_id)
        return {
            "status": "success",
            "message": f"Progress saved for user {user_id}",
            "storage": "firestore",
        }

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO learning_progress
        (user_id, topic, activity_type, notes, score, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, payload["topic"], payload["activity_type"], payload["notes"], score, created_at),
    )
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "message": f"Progress saved for user {user_id}",
        "storage": "sqlite_fallback",
    }


def get_learning_history(user_id: str, limit: int = 10) -> dict[str, Any]:
    db = get_firestore_client()
    if db:
        records = []
        docs = (
            _user_progress_collection(db, user_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        for doc in docs:
            record = doc.to_dict()
            record["record_id"] = doc.id
            records.append(record)
        return {"status": "success", "history": records}

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, topic, activity_type, notes, score, created_at
        FROM learning_progress
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    history = [
        {
            "record_id": row[0],
            "topic": row[1],
            "activity_type": row[2],
            "notes": row[3],
            "score": row[4],
            "created_at": row[5],
        }
        for row in rows
    ]
    return {"status": "success", "history": history}


def delete_learning_history_item(user_id: str, record_id: str) -> dict[str, Any]:
    normalized_record_id = str(record_id).strip()
    if not normalized_record_id:
        return {"status": "error", "message": "Missing history record id."}

    db = get_firestore_client()
    if db:
        record_ref = _user_progress_collection(db, user_id).document(normalized_record_id)
        snapshot = record_ref.get()
        if not snapshot.exists:
            return {"status": "not_found", "message": "History record not found."}
        record_ref.delete()
        return {
            "status": "success",
            "message": "Previous session deleted.",
            "record_id": normalized_record_id,
            "storage": "firestore",
        }

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM learning_progress
        WHERE user_id = ? AND id = ?
        """,
        (user_id, normalized_record_id),
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    if not deleted:
        return {"status": "not_found", "message": "History record not found."}
    return {
        "status": "success",
        "message": "Previous session deleted.",
        "record_id": normalized_record_id,
        "storage": "sqlite_fallback",
    }


def delete_all_learning_history(user_id: str) -> dict[str, Any]:
    db = get_firestore_client()
    if db:
        docs = list(_user_progress_collection(db, user_id).stream())
        for doc in docs:
            doc.reference.delete()
        return {
            "status": "success",
            "message": "All previous sessions deleted.",
            "deleted_count": len(docs),
            "storage": "firestore",
        }

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM learning_progress
        WHERE user_id = ?
        """,
        (user_id,),
    )
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "message": "All previous sessions deleted.",
        "deleted_count": deleted,
        "storage": "sqlite_fallback",
    }


def save_study_note(user_id: str, topic: str, note: str) -> dict[str, Any]:
    created_at = _utc_now()
    payload = {
        "topic": str(topic).strip(),
        "note": str(note).strip(),
        "created_at": created_at,
    }

    db = get_firestore_client()
    if db:
        _user_notes_collection(db, user_id).add(payload)
        _touch_user_doc(db, user_id)
        return {
            "status": "success",
            "message": f"Note saved for {user_id}",
            "topic": payload["topic"],
            "storage": "firestore",
        }

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO study_notes (user_id, topic, note, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, payload["topic"], payload["note"], created_at),
    )
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "message": f"Note saved for {user_id}",
        "topic": payload["topic"],
        "storage": "sqlite_fallback",
    }


def list_study_notes(user_id: str, limit: int = 10) -> dict[str, Any]:
    db = get_firestore_client()
    if db:
        notes = []
        docs = (
            _user_notes_collection(db, user_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        for doc in docs:
            notes.append(doc.to_dict())
        return {"status": "success", "notes": notes}

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT topic, note, created_at
        FROM study_notes
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    notes = [{"topic": row[0], "note": row[1], "created_at": row[2]} for row in rows]
    return {"status": "success", "notes": notes}


def create_assessment(
    user_id: str,
    topic: str,
    assessment_type: str = "diagnostic",
    level: str = "beginner",
    goal: str = "",
    available_time: int | None = None,
    learning_style: str = "balanced",
    question_count: int = 5,
) -> dict[str, Any]:
    normalized_type = str(assessment_type).strip().lower() or "diagnostic"
    normalized_topic = str(topic).strip() or "general learning"
    try:
        question_count = max(3, min(7, int(question_count)))
    except (TypeError, ValueError):
        question_count = 5

    save_learner_profile(
        user_id=user_id,
        topic=normalized_topic,
        level=level,
        learning_style=learning_style,
        available_time=available_time,
        goal=goal,
    )

    questions = _generate_questions_with_model(
        topic=normalized_topic,
        level=level,
        goal=goal,
        available_time=available_time,
        assessment_type=normalized_type,
        question_count=question_count,
    )
    created_at = _utc_now()
    assessment_id = str(uuid.uuid4())
    record = {
        "assessment_id": assessment_id,
        "user_id": user_id,
        "topic": normalized_topic,
        "assessment_type": normalized_type,
        "level": level,
        "goal": goal,
        "learning_style": learning_style,
        "available_time": available_time,
        "status": "open",
        "question_count": len(questions),
        "questions": questions,
        "created_at": created_at,
        "submitted_at": "",
        "score": None,
    }

    db = get_firestore_client()
    if db:
        _user_assessments_collection(db, user_id).document(assessment_id).set(record)
        _touch_user_doc(db, user_id)
    else:
        init_sqlite_fallback()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO assessments
            (assessment_id, user_id, topic, assessment_type, level, goal, status, question_count, questions_json, answers_json, result_json, score, created_at, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assessment_id,
                user_id,
                normalized_topic,
                normalized_type,
                level,
                goal,
                "open",
                len(questions),
                json.dumps(questions),
                json.dumps({}),
                json.dumps({}),
                None,
                created_at,
                "",
            ),
        )
        conn.commit()
        conn.close()

    return {
        "status": "success",
        "assessment_id": assessment_id,
        "assessment_type": normalized_type,
        "topic": normalized_topic,
        "level": level,
        "goal": goal,
        "questions": _public_questions(questions),
        "question_count": len(questions),
    }


def create_custom_assessment(
    user_id: str,
    topic: str,
    questions: list[dict[str, Any]],
    assessment_type: str = "mock_test",
    level: str = "beginner",
    goal: str = "",
    available_time: int | None = None,
    learning_style: str = "balanced",
) -> dict[str, Any]:
    normalized_type = str(assessment_type).strip().lower() or "mock_test"
    normalized_topic = str(topic).strip() or "general learning"

    normalized_questions: list[dict[str, Any]] = []
    for index, question in enumerate(questions or []):
        question_type = str(question.get("question_type", "multiple_choice")).strip().lower() or "multiple_choice"
        if question_type not in {"multiple_choice", "short_answer", "essay"}:
            question_type = "multiple_choice"
        options = [str(option).strip() for option in (question.get("options") or [])][:4]
        answer = str(question.get("correct_answer", "")).strip()
        if question_type == "multiple_choice":
            if len(options) != 4:
                continue
            answer = answer.upper()[:1]
            if answer not in {"A", "B", "C", "D"}:
                answer = "A"
        else:
            options = []
            if not answer:
                answer = str(question.get("grading_guide", "")).strip() or "See grading guide."
        normalized_questions.append(
            {
                "question_id": f"q{index + 1}",
                "question_type": question_type,
                "prompt": str(question.get("prompt", "")).strip(),
                "options": options,
                "correct_answer": answer,
                "explanation": str(question.get("explanation", "")).strip(),
                "concept": str(question.get("concept", "general")).strip() or "general",
                "difficulty": str(question.get("difficulty", level)).strip() or level,
                "grading_guide": str(question.get("grading_guide", "")).strip(),
            }
        )

    if not normalized_questions:
        return {"status": "error", "message": "No valid questions were generated."}

    save_learner_profile(
        user_id=user_id,
        topic=normalized_topic,
        level=level,
        learning_style=learning_style,
        available_time=available_time,
        goal=goal,
    )

    created_at = _utc_now()
    assessment_id = str(uuid.uuid4())
    record = {
        "assessment_id": assessment_id,
        "user_id": user_id,
        "topic": normalized_topic,
        "assessment_type": normalized_type,
        "level": level,
        "goal": goal,
        "learning_style": learning_style,
        "available_time": available_time,
        "status": "open",
        "question_count": len(normalized_questions),
        "questions": normalized_questions,
        "created_at": created_at,
        "submitted_at": "",
        "score": None,
    }

    db = get_firestore_client()
    if db:
        _user_assessments_collection(db, user_id).document(assessment_id).set(record)
        _touch_user_doc(db, user_id)
    else:
        init_sqlite_fallback()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO assessments
            (assessment_id, user_id, topic, assessment_type, level, goal, status, question_count, questions_json, answers_json, result_json, score, created_at, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assessment_id,
                user_id,
                normalized_topic,
                normalized_type,
                level,
                goal,
                "open",
                len(normalized_questions),
                json.dumps(normalized_questions),
                json.dumps({}),
                json.dumps({}),
                None,
                created_at,
                "",
            ),
        )
        conn.commit()
        conn.close()

    return {
        "status": "success",
        "assessment_id": assessment_id,
        "assessment_type": normalized_type,
        "topic": normalized_topic,
        "level": level,
        "goal": goal,
        "questions": _public_questions(normalized_questions),
        "question_count": len(normalized_questions),
    }


def _grade_open_response(question: dict[str, Any], learner_answer: str) -> tuple[float, str, str]:
    answer_text = str(learner_answer or "").strip()
    if not answer_text:
        return 0.0, "No answer submitted.", str(question.get("correct_answer", "")).strip()

    client = _get_genai_client()
    expected = str(question.get("correct_answer", "")).strip()
    guide = str(question.get("grading_guide", "")).strip()
    if client:
        schema = {
            "type": "object",
            "properties": {
                "score": {"type": "number"},
                "feedback": {"type": "string"},
                "expected_answer": {"type": "string"},
            },
            "required": ["score", "feedback", "expected_answer"],
        }
        prompt = f"""
Grade this learner response.

Question: {question.get('prompt', '')}
Question type: {question.get('question_type', 'short_answer')}
Expected answer: {expected}
Grading guide: {guide}
Learner answer: {answer_text}

Return JSON only with:
- score: between 0 and 1
- feedback: short feedback
- expected_answer: short ideal answer
"""
        try:
            response = client.models.generate_content(
                model=QUIZ_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    responseMimeType="application/json",
                    responseSchema=schema,
                ),
            )
            payload = json.loads(response.text)
            score = max(0.0, min(1.0, _safe_float(payload.get("score"), 0.0)))
            feedback = str(payload.get("feedback", "")).strip() or "Reviewed."
            expected_answer = str(payload.get("expected_answer", "")).strip() or expected
            return score, feedback, expected_answer
        except Exception:
            pass

    keywords = {
        token for token in re.findall(r"[a-zA-Z0-9]+", f"{expected} {guide}".lower()) if len(token) > 3
    }
    answer_words = {token for token in re.findall(r"[a-zA-Z0-9]+", answer_text.lower()) if len(token) > 3}
    overlap = len(keywords & answer_words)
    ratio = overlap / max(1, len(keywords)) if keywords else 0.5
    score = 1.0 if ratio >= 0.6 else 0.6 if ratio >= 0.3 else 0.2
    feedback = "Good coverage." if score >= 0.8 else "Partially correct." if score >= 0.5 else "Needs more detail."
    return score, feedback, expected


def _get_assessment_record(user_id: str, assessment_id: str) -> dict[str, Any] | None:
    db = get_firestore_client()
    if db:
        snapshot = _user_assessments_collection(db, user_id).document(assessment_id).get()
        if snapshot.exists:
            return snapshot.to_dict()
        return None

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_id, topic, assessment_type, level, goal, status, question_count, questions_json, answers_json, result_json, score, created_at, submitted_at
        FROM assessments
        WHERE assessment_id = ? AND user_id = ?
        """,
        (assessment_id, user_id),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "assessment_id": assessment_id,
        "user_id": row[0],
        "topic": row[1],
        "assessment_type": row[2],
        "level": row[3],
        "goal": row[4],
        "status": row[5],
        "question_count": row[6],
        "questions": json.loads(row[7] or "[]"),
        "answers": json.loads(row[8] or "{}"),
        "result": json.loads(row[9] or "{}"),
        "score": row[10],
        "created_at": row[11],
        "submitted_at": row[12],
    }


def submit_assessment(
    user_id: str,
    assessment_id: str,
    answers: dict[str, str],
    confidence_by_question: dict[str, float] | None = None,
) -> dict[str, Any]:
    record = _get_assessment_record(user_id, assessment_id)
    if not record:
        return {"status": "error", "message": "Assessment not found."}
    if record.get("status") == "submitted":
        return {
            "status": "success",
            "message": "Assessment already submitted.",
            "result": record.get("result", {}),
        }

    confidence_by_question = confidence_by_question or {}
    normalized_answers = {
        str(question_id): str(answer).strip() for question_id, answer in (answers or {}).items()
    }

    question_results = []
    earned_score_total = 0.0
    correct_count = 0.0
    concept_totals: dict[str, list[float]] = {}
    for question in record.get("questions", []):
        question_id = question["question_id"]
        selected = normalized_answers.get(question_id, "")
        question_type = question.get("question_type", "multiple_choice")
        correct = question.get("correct_answer", "A")
        if question_type == "multiple_choice":
            normalized_selected = selected.upper()[:1]
            is_correct = normalized_selected == correct
            numeric_score = 1.0 if is_correct else 0.0
            feedback = question.get("explanation", "")
            expected_answer = correct
            selected_value = normalized_selected or "No answer"
        else:
            numeric_score, feedback, expected_answer = _grade_open_response(question, selected)
            is_correct = numeric_score >= 0.7
            selected_value = selected or "No answer"
        earned_score_total += numeric_score
        if is_correct:
            correct_count += 1
        concept = question.get("concept", "general")
        concept_totals.setdefault(concept, [0.0, 0.0])
        concept_totals[concept][0] += numeric_score
        concept_totals[concept][1] += 1.0
        question_results.append(
            {
                "question_id": question_id,
                "concept": concept,
                "question_type": question_type,
                "selected_answer": selected_value,
                "correct_answer": expected_answer,
                "is_correct": is_correct,
                "score": round(numeric_score, 3),
                "explanation": feedback or question.get("explanation", ""),
                "confidence": _safe_float(confidence_by_question.get(question_id), 0.0),
            }
        )

    question_count = max(1, len(record.get("questions", [])))
    score = round(earned_score_total / question_count, 3)
    concept_accuracy = {
        concept: round(values[0] / values[1], 3) if values[1] else 0.0
        for concept, values in concept_totals.items()
    }
    weak_concepts = [concept for concept, value in concept_accuracy.items() if value < 0.7]
    mastery = _update_mastery_from_assessment(
        user_id=user_id,
        topic=record.get("topic", "general"),
        assessment_type=record.get("assessment_type", "diagnostic"),
        concept_accuracy=concept_accuracy,
        score=score,
    )

    result = {
        "assessment_id": assessment_id,
        "topic": record.get("topic", "general"),
        "assessment_type": record.get("assessment_type", "diagnostic"),
        "score": score,
        "correct_count": round(correct_count, 2),
        "question_count": question_count,
        "concept_accuracy": concept_accuracy,
        "weak_concepts": weak_concepts,
        "question_results": question_results,
        "recommended_next_action": (
            f"Review {weak_concepts[0]} with a short remedial lesson."
            if weak_concepts
            else f"Move to the next lesson on {record.get('topic', 'this topic')}."
        ),
    }

    submitted_at = _utc_now()
    db = get_firestore_client()
    if db:
        _user_assessments_collection(db, user_id).document(assessment_id).set(
            {
                "status": "submitted",
                "answers": normalized_answers,
                "result": result,
                "score": score,
                "submitted_at": submitted_at,
            },
            merge=True,
        )
        _touch_user_doc(db, user_id)
    else:
        init_sqlite_fallback()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE assessments
            SET status = ?, answers_json = ?, result_json = ?, score = ?, submitted_at = ?
            WHERE assessment_id = ? AND user_id = ?
            """,
            (
                "submitted",
                json.dumps(normalized_answers),
                json.dumps(result),
                score,
                submitted_at,
                assessment_id,
                user_id,
            ),
        )
        conn.commit()
        conn.close()

    save_learning_progress(
        user_id=user_id,
        topic=record.get("topic", "general"),
        activity_type=record.get("assessment_type", "diagnostic"),
        notes=f"Assessment score: {correct_count}/{question_count}. Weak concepts: {', '.join(weak_concepts) or 'none'}",
        score=score,
    )

    return {
        "status": "success",
        "result": result,
        "mastery": mastery,
    }


def get_mastery_snapshot(user_id: str) -> dict[str, Any]:
    mastery = _load_mastery(user_id)
    topics = mastery.get("topics", {})
    ordered_topics = sorted(
        topics.values(),
        key=lambda item: (item.get("updated_at", ""), item.get("score", 0.0)),
        reverse=True,
    )
    return {
        "status": "success",
        "overall_score": mastery.get("overall_score", 0.0),
        "overall_label": mastery.get("overall_label", _score_label(_safe_float(mastery.get("overall_score"), 0.0))),
        "topics": ordered_topics,
        "updated_at": mastery.get("updated_at", ""),
    }


def _load_roadmap(user_id: str) -> dict[str, Any] | None:
    db = get_firestore_client()
    if db:
        snapshot = _user_roadmap_doc(db, user_id).get()
        if snapshot.exists:
            return (snapshot.to_dict() or {}).get("roadmap")
        return None

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT roadmap_json FROM learner_roadmaps WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row or not row[0]:
        return None
    try:
        return json.loads(row[0])
    except json.JSONDecodeError:
        return None


def _save_roadmap(user_id: str, roadmap: dict[str, Any]) -> None:
    roadmap["updated_at"] = _utc_now()
    roadmap_id = str(roadmap.get("roadmap_id") or "").strip()
    db = get_firestore_client()
    if db:
        _user_roadmap_doc(db, user_id).set(
            {"roadmap": roadmap, "updated_at": roadmap["updated_at"]},
            merge=True,
        )
        if roadmap_id:
            _user_roadmaps_collection(db, user_id).document(roadmap_id).set(
                {
                    "roadmap": roadmap,
                    "created_at": roadmap.get("created_at", roadmap["updated_at"]),
                    "updated_at": roadmap["updated_at"],
                },
                merge=True,
            )
        _touch_user_doc(db, user_id)
        return

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO learner_roadmaps (user_id, roadmap_json, updated_at)
        VALUES (?, ?, ?)
        """,
        (user_id, json.dumps(roadmap), roadmap["updated_at"]),
    )
    if roadmap_id:
        cur.execute(
            """
            INSERT OR REPLACE INTO learner_roadmap_history
            (user_id, roadmap_id, roadmap_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                roadmap_id,
                json.dumps(roadmap),
                roadmap.get("created_at", roadmap["updated_at"]),
                roadmap["updated_at"],
            ),
        )
    conn.commit()
    conn.close()


def list_roadmaps(user_id: str) -> dict[str, Any]:
    roadmaps: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    current = _load_roadmap(user_id)
    current_id = str((current or {}).get("roadmap_id") or "").strip()

    db = get_firestore_client()
    if db:
        for snapshot in _user_roadmaps_collection(db, user_id).stream():
            if snapshot.id == "current":
                continue
            roadmap = (snapshot.to_dict() or {}).get("roadmap") or {}
            roadmap_id = str(roadmap.get("roadmap_id") or snapshot.id).strip()
            if roadmap_id == current_id:
                continue
            if roadmap and roadmap_id and roadmap_id not in seen_ids:
                seen_ids.add(roadmap_id)
                roadmaps.append(roadmap)
    else:
        init_sqlite_fallback()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT roadmap_json
            FROM learner_roadmap_history
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()
        conn.close()
        for row in rows:
            try:
                roadmap = json.loads(row[0] or "{}")
            except json.JSONDecodeError:
                continue
            roadmap_id = str(roadmap.get("roadmap_id") or "").strip()
            if roadmap_id == current_id:
                continue
            if roadmap and roadmap_id and roadmap_id not in seen_ids:
                seen_ids.add(roadmap_id)
                roadmaps.append(roadmap)

    roadmaps.sort(
        key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
        reverse=True,
    )
    return {
        "status": "success",
        "roadmaps": [
            {
                "roadmap": roadmap,
                "summary": _roadmap_summary(roadmap),
                "is_current": str(roadmap.get("roadmap_id") or "") == current_id,
            }
            for roadmap in roadmaps
        ],
    }


def delete_saved_roadmap(user_id: str, roadmap_id: str) -> dict[str, Any]:
    normalized_roadmap_id = str(roadmap_id or "").strip()
    if not normalized_roadmap_id:
        return {"status": "error", "message": "Missing roadmap id."}

    current = _load_roadmap(user_id) or {}
    if str(current.get("roadmap_id") or "").strip() == normalized_roadmap_id:
        return {
            "status": "error",
            "message": "This is your current roadmap. Use Delete on the current roadmap card instead.",
        }

    db = get_firestore_client()
    if db:
        doc = _user_roadmaps_collection(db, user_id).document(normalized_roadmap_id)
        snapshot = doc.get()
        if not snapshot.exists:
            return {"status": "not_found", "message": "Saved roadmap not found."}
        doc.delete()
        _touch_user_doc(db, user_id)
        return {"status": "success", "message": "Saved roadmap removed."}

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM learner_roadmap_history WHERE user_id = ? AND roadmap_id = ?",
        (user_id, normalized_roadmap_id),
    )
    deleted_count = cur.rowcount
    conn.commit()
    conn.close()
    if not deleted_count:
        return {"status": "not_found", "message": "Saved roadmap not found."}
    return {"status": "success", "message": "Saved roadmap removed."}


def delete_all_saved_roadmaps(user_id: str) -> dict[str, Any]:
    current = _load_roadmap(user_id) or {}
    current_id = str(current.get("roadmap_id") or "").strip()
    deleted_count = 0

    db = get_firestore_client()
    if db:
        for snapshot in _user_roadmaps_collection(db, user_id).stream():
            if snapshot.id == "current" or snapshot.id == current_id:
                continue
            roadmap = (snapshot.to_dict() or {}).get("roadmap") or {}
            roadmap_id = str(roadmap.get("roadmap_id") or snapshot.id).strip()
            if roadmap_id and roadmap_id == current_id:
                continue
            snapshot.reference.delete()
            deleted_count += 1
        if deleted_count:
            _touch_user_doc(db, user_id)
        return {
            "status": "success",
            "message": (
                f"Deleted {deleted_count} saved roadmap{'s' if deleted_count != 1 else ''}."
                if deleted_count
                else "No previous saved roadmaps to delete."
            ),
        }

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    if current_id:
        cur.execute(
            "DELETE FROM learner_roadmap_history WHERE user_id = ? AND roadmap_id != ?",
            (user_id, current_id),
        )
    else:
        cur.execute("DELETE FROM learner_roadmap_history WHERE user_id = ?", (user_id,))
    deleted_count = cur.rowcount
    conn.commit()
    conn.close()
    return {
        "status": "success",
        "message": (
            f"Deleted {deleted_count} saved roadmap{'s' if deleted_count != 1 else ''}."
            if deleted_count
            else "No previous saved roadmaps to delete."
        ),
    }


def update_saved_roadmap_session(
    user_id: str,
    roadmap_id: str,
    phase_id: str,
    session_id: str,
    status: str,
) -> dict[str, Any]:
    normalized_roadmap_id = str(roadmap_id or "").strip()
    normalized_status = str(status or "").strip().lower()
    if not normalized_roadmap_id:
        return {"status": "error", "message": "Missing roadmap id."}
    if normalized_status not in {"planned", "completed", "missed"}:
        return {"status": "error", "message": "Invalid session status."}

    current = _load_roadmap(user_id) or {}
    if str(current.get("roadmap_id") or "").strip() == normalized_roadmap_id:
        return update_roadmap_session(user_id, phase_id, session_id, normalized_status)

    db = get_firestore_client()
    if db:
        doc = _user_roadmaps_collection(db, user_id).document(normalized_roadmap_id)
        snapshot = doc.get()
        if not snapshot.exists:
            return {"status": "not_found", "message": "Saved roadmap not found."}
        payload = snapshot.to_dict() or {}
        roadmap = payload.get("roadmap") or {}
    else:
        init_sqlite_fallback()
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "SELECT roadmap_json FROM learner_roadmap_history WHERE user_id = ? AND roadmap_id = ?",
            (user_id, normalized_roadmap_id),
        )
        row = cur.fetchone()
        conn.close()
        if not row or not row[0]:
            return {"status": "not_found", "message": "Saved roadmap not found."}
        try:
            roadmap = json.loads(row[0])
        except json.JSONDecodeError:
            return {"status": "error", "message": "Saved roadmap data is unreadable."}

    updated = False
    for phase in roadmap.get("phases", []):
        if phase.get("phase_id") != phase_id:
            continue
        for session in phase.get("sessions", []):
            if session.get("session_id") == session_id:
                session["status"] = normalized_status
                updated = True
                break
        if updated:
            break

    if not updated:
        return {"status": "error", "message": "Session not found."}

    roadmap["updated_at"] = _utc_now()
    summary = _roadmap_summary(roadmap)
    roadmap["status"] = "completed" if summary["completion_rate"] >= 1 else "active"

    if db:
        doc.set(
            {
                "roadmap": roadmap,
                "created_at": roadmap.get("created_at", roadmap["updated_at"]),
                "updated_at": roadmap["updated_at"],
            },
            merge=True,
        )
        _touch_user_doc(db, user_id)
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE learner_roadmap_history
            SET roadmap_json = ?, updated_at = ?
            WHERE user_id = ? AND roadmap_id = ?
            """,
            (json.dumps(roadmap), roadmap["updated_at"], user_id, normalized_roadmap_id),
        )
        conn.commit()
        conn.close()

    return {
        "status": "success",
        "roadmap": roadmap,
        "summary": summary,
        "message": "Saved roadmap session updated.",
    }


def delete_roadmap(user_id: str) -> dict[str, Any]:
    db = get_firestore_client()
    if db:
        snapshot = _user_roadmap_doc(db, user_id).get()
        if not snapshot.exists:
            return {"status": "not_found", "message": "No roadmap found."}
        roadmap = (snapshot.to_dict() or {}).get("roadmap") or {}
        roadmap_id = str(roadmap.get("roadmap_id") or "").strip()
        _user_roadmap_doc(db, user_id).delete()
        if roadmap_id:
            _user_roadmaps_collection(db, user_id).document(roadmap_id).delete()
        _touch_user_doc(db, user_id)
        return {"status": "success", "message": "Roadmap deleted."}

    init_sqlite_fallback()
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT roadmap_json FROM learner_roadmaps WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    roadmap_id = ""
    if row:
        try:
            roadmap_id = str((json.loads(row[0] or "{}")).get("roadmap_id") or "").strip()
        except json.JSONDecodeError:
            roadmap_id = ""
    cur.execute("DELETE FROM learner_roadmaps WHERE user_id = ?", (user_id,))
    deleted_count = cur.rowcount
    if roadmap_id:
        cur.execute(
            "DELETE FROM learner_roadmap_history WHERE user_id = ? AND roadmap_id = ?",
            (user_id, roadmap_id),
        )
    conn.commit()
    conn.close()
    if not deleted_count:
        return {"status": "not_found", "message": "No roadmap found."}
    return {"status": "success", "message": "Roadmap deleted."}


def _today_iso_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _date_plus_days(days: int, start_date: str = "") -> str:
    base_date = datetime.now(timezone.utc).date()
    if start_date:
        try:
            base_date = datetime.fromisoformat(str(start_date).strip()).date()
        except ValueError:
            base_date = datetime.now(timezone.utc).date()
    return (base_date + timedelta(days=days)).isoformat()


def _phase_title(index: int) -> str:
    return ["Foundation", "Practice", "Checkpoint", "Extension"][min(index, 3)]


def _build_roadmap_phases(
    topic: str,
    goal: str,
    level: str,
    available_time: int | None,
    deadline_days: int,
    weak_topics: list[str],
    recovery_mode: bool,
    start_date: str = "",
) -> list[dict[str, Any]]:
    topic_label = topic or "your target topic"
    focus_topics = weak_topics[:] if weak_topics else [topic_label]
    total_phases = 2 if recovery_mode else (3 if deadline_days > 10 else 2)
    phases = []
    spacing = max(2, deadline_days // max(total_phases, 1))
    minutes = available_time or 45

    for index in range(total_phases):
        phase_id = f"phase-{index + 1}"
        due_offset = min(deadline_days, spacing * (index + 1))
        primary_focus = focus_topics[min(index, len(focus_topics) - 1)] if focus_topics else topic_label
        checkpoint_type = "recovery quiz" if recovery_mode and index == total_phases - 1 else "mastery quiz"
        session_total = 2 if recovery_mode else 3
        sessions = []
        for session_index in range(session_total):
            session_id = f"{phase_id}-session-{session_index + 1}"
            sessions.append(
                {
                    "session_id": session_id,
                    "title": f"{primary_focus.title()} session {session_index + 1}",
                    "focus": primary_focus,
                    "duration_minutes": minutes,
                    "status": "planned",
                    "due_date": _date_plus_days(
                        min(deadline_days, index * spacing + session_index + 1),
                        start_date=start_date,
                    ),
                }
            )

        phases.append(
            {
                "phase_id": phase_id,
                "title": f"{_phase_title(index)} {index + 1}",
                "goal": (
                    f"Rebuild confidence in {primary_focus} and recover momentum."
                    if recovery_mode
                    else f"Move {topic_label} from {level} understanding toward stronger applied mastery."
                ),
                "focus_topics": [primary_focus],
                "expected_outcome": (
                    f"Learner can explain and apply {primary_focus} in a short exercise."
                ),
                "checkpoint_type": checkpoint_type,
                "checkpoint_due_date": _date_plus_days(due_offset, start_date=start_date),
                "sessions": sessions,
            }
        )
    return phases


def _roadmap_summary(roadmap: dict[str, Any]) -> dict[str, Any]:
    phases = roadmap.get("phases", [])
    total_sessions = 0
    completed_sessions = 0
    missed_sessions = 0
    upcoming = []
    for phase in phases:
        for session in phase.get("sessions", []):
            total_sessions += 1
            status = session.get("status", "planned")
            if status == "completed":
                completed_sessions += 1
            if status == "missed":
                missed_sessions += 1
            if status == "planned":
                upcoming.append(session)
    completion_rate = round(completed_sessions / total_sessions, 3) if total_sessions else 0.0
    next_session = upcoming[0] if upcoming else {}
    return {
        "mode": roadmap.get("mode", "standard"),
        "status": roadmap.get("status", "active"),
        "phase_count": len(phases),
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "missed_sessions": missed_sessions,
        "completion_rate": completion_rate,
        "next_session": next_session,
        "revision_reason": roadmap.get("revision_reason", ""),
        "updated_at": roadmap.get("updated_at", ""),
    }


def _should_recover(roadmap: dict[str, Any], weak_topics: list[str]) -> tuple[bool, str]:
    summary = _roadmap_summary(roadmap)
    if summary["missed_sessions"] >= 2:
        return True, "missed multiple planned study sessions"
    if weak_topics and roadmap.get("mode") != "recovery":
        return True, f"new weak topics detected: {', '.join(weak_topics[:2])}"
    return False, ""


def build_or_update_roadmap(
    user_id: str,
    topic: str = "",
    goal: str = "",
    level: str = "",
    available_time: int | None = None,
    deadline_days: int = 14,
    start_date: str = "",
    force_rebuild: bool = False,
    revision_reason: str = "",
    recovery_mode_override: bool | None = None,
) -> dict[str, Any]:
    profile_result = get_learner_profile(user_id)
    profile = profile_result if profile_result.get("status") == "success" else {}
    mastery = get_mastery_snapshot(user_id)
    weak_topics = [item.get("topic", "") for item in mastery.get("topics", []) if item.get("score", 0.0) < 0.65][:3]
    current = _load_roadmap(user_id)

    normalized_topic = str(topic).strip() or profile.get("topic") or (weak_topics[0] if weak_topics else "General learning")
    normalized_goal = str(goal).strip() or profile.get("goal") or f"Build stronger mastery in {normalized_topic}"
    normalized_level = str(level).strip() or profile.get("level") or "beginner"
    normalized_time = available_time if available_time not in ("", None) else profile.get("available_time")
    normalized_time = _safe_int(normalized_time, 45) or 45
    deadline_days = max(7, min(60, _safe_int(deadline_days, 14) or 14))
    normalized_start_date = str(start_date).strip()
    if normalized_start_date:
        try:
            datetime.fromisoformat(normalized_start_date).date()
        except ValueError:
            normalized_start_date = ""

    recovery_mode = bool(recovery_mode_override) if recovery_mode_override is not None else False
    auto_reason = revision_reason
    current_topic = str((current or {}).get("topic") or "").strip().lower()
    requested_topic = str(normalized_topic or "").strip().lower()
    is_new_topic_request = bool(current and requested_topic and requested_topic != current_topic)

    if current and not force_rebuild and not is_new_topic_request:
        recovery_mode, auto_reason = _should_recover(current, weak_topics)
        if not recovery_mode:
            return {
                "status": "success",
                "roadmap": current,
                "summary": _roadmap_summary(current),
                "message": "Existing roadmap is still active.",
            }

    if recovery_mode_override is not None:
        recovery_mode = bool(recovery_mode_override)

    if not auto_reason:
        auto_reason = "manual refresh" if force_rebuild else "first roadmap"

    save_learner_profile(
        user_id=user_id,
        topic=normalized_topic,
        level=normalized_level,
        learning_style=profile.get("learning_style", "balanced"),
        available_time=normalized_time,
        goal=normalized_goal,
        target_date=normalized_start_date or profile.get("target_date", ""),
    )

    phases = _build_roadmap_phases(
        topic=normalized_topic,
        goal=normalized_goal,
        level=normalized_level,
        available_time=normalized_time,
        deadline_days=deadline_days,
        weak_topics=weak_topics,
        recovery_mode=recovery_mode,
        start_date=normalized_start_date,
    )
    roadmap = {
        "roadmap_id": str(uuid.uuid4()),
        "topic": normalized_topic,
        "goal": normalized_goal,
        "level": normalized_level,
        "available_time": normalized_time,
        "deadline_days": deadline_days,
        "start_date": normalized_start_date,
        "mode": "recovery" if recovery_mode else "standard",
        "status": "active",
        "revision_reason": auto_reason,
        "created_at": _utc_now(),
        "phases": phases,
    }
    _save_roadmap(user_id, roadmap)
    return {
        "status": "success",
        "roadmap": roadmap,
        "summary": _roadmap_summary(roadmap),
        "message": "Recovery roadmap generated." if recovery_mode else "Roadmap generated.",
    }


def get_roadmap(user_id: str) -> dict[str, Any]:
    roadmap = _load_roadmap(user_id)
    if not roadmap:
        return {"status": "not_found", "message": "No roadmap found."}
    return {
        "status": "success",
        "roadmap": roadmap,
        "summary": _roadmap_summary(roadmap),
    }


def update_roadmap_session(
    user_id: str,
    phase_id: str,
    session_id: str,
    status: str,
) -> dict[str, Any]:
    roadmap = _load_roadmap(user_id)
    if not roadmap:
        return {"status": "error", "message": "No roadmap found."}

    normalized_status = str(status).strip().lower()
    if normalized_status not in {"planned", "completed", "missed"}:
        return {"status": "error", "message": "Invalid session status."}

    updated = False
    topic = roadmap.get("topic", "General learning")
    for phase in roadmap.get("phases", []):
        if phase.get("phase_id") != phase_id:
            continue
        for session in phase.get("sessions", []):
            if session.get("session_id") == session_id:
                session["status"] = normalized_status
                updated = True
                break

    if not updated:
        return {"status": "error", "message": "Session not found."}

    roadmap["updated_at"] = _utc_now()
    summary = _roadmap_summary(roadmap)
    roadmap["status"] = "completed" if summary["completion_rate"] >= 1 else "active"
    _save_roadmap(user_id, roadmap)

    if normalized_status == "completed":
        save_learning_progress(
            user_id=user_id,
            topic=topic,
            activity_type="roadmap_session",
            notes=f"Completed {session_id} from {phase_id}",
            score=None,
        )
    elif normalized_status == "missed":
        save_learning_progress(
            user_id=user_id,
            topic=topic,
            activity_type="missed_session",
            notes=f"Missed {session_id} from {phase_id}",
            score=0.0,
        )

    weak_topics = [item.get("topic", "") for item in get_mastery_snapshot(user_id).get("topics", []) if item.get("score", 0.0) < 0.65][:3]
    trigger_recovery, reason = _should_recover(roadmap, weak_topics)
    if trigger_recovery and roadmap.get("mode") != "recovery":
        rebuilt = build_or_update_roadmap(
            user_id=user_id,
            topic=topic,
            force_rebuild=True,
            revision_reason=reason,
            recovery_mode_override=True,
        )
        rebuilt["message"] = f"Roadmap updated: {reason}."
        return rebuilt

    return {
        "status": "success",
        "roadmap": roadmap,
        "summary": _roadmap_summary(roadmap),
        "message": "Roadmap session updated.",
    }


def get_intervention_plan(user_id: str) -> dict[str, Any]:
    state = get_learner_state(user_id)
    if state.get("status") != "success":
        return {"status": "error", "message": "Learner state unavailable."}

    mastery = state.get("mastery", {})
    roadmap_summary = state.get("roadmap_summary", {})
    overall_score = _safe_float(mastery.get("overall_score"), 0.0)
    weak_topics = state.get("weak_topics", [])
    missed_sessions = _safe_int(roadmap_summary.get("missed_sessions"), 0)
    completed_sessions = _safe_int(roadmap_summary.get("completed_sessions"), 0)
    history = get_learning_history(user_id, limit=10).get("history", [])

    low_scores = [
        item for item in history
        if item.get("score") is not None and _safe_float(item.get("score"), 1.0) < 0.65
    ]

    risk_level = "low"
    triggers = []
    if missed_sessions >= 2:
        risk_level = "high"
        triggers.append("multiple missed roadmap sessions")
    if overall_score < 0.55:
        risk_level = "high"
        triggers.append("low overall mastery")
    elif overall_score < 0.7 and risk_level != "high":
        risk_level = "medium"
        triggers.append("developing mastery")
    if len(low_scores) >= 2 and risk_level != "high":
        risk_level = "medium"
        triggers.append("repeated low assessment scores")
    if weak_topics:
        triggers.append(f"weak topics: {', '.join(weak_topics[:3])}")

    recommended_actions = []
    if risk_level == "high":
        recommended_actions.extend(
            [
                "Switch to a shorter recovery roadmap focused on one or two high-impact topics.",
                "Schedule one focused catch-up session in Google Calendar.",
                "Create Google Tasks for the next two study sessions only.",
            ]
        )
    elif risk_level == "medium":
        recommended_actions.extend(
            [
                "Run a short remediation lesson on the weakest topic.",
                "Take a follow-up checkpoint quiz after the next study session.",
                "Tighten the roadmap by prioritizing practice over breadth.",
            ]
        )
    else:
        recommended_actions.extend(
            [
                "Continue with the next roadmap session.",
                "Keep a weekly progress report and checkpoint quiz cadence.",
            ]
        )

    summary = (
        f"Risk level: {risk_level}. "
        f"Completed sessions: {completed_sessions}. Missed sessions: {missed_sessions}. "
        f"Overall mastery: {round(overall_score * 100)}%."
    )
    return {
        "status": "success",
        "risk_level": risk_level,
        "triggers": triggers,
        "recommended_actions": recommended_actions,
        "summary": summary,
    }


def generate_weekly_report(user_id: str) -> dict[str, Any]:
    state = get_learner_state(user_id)
    if state.get("status") != "success":
        return {"status": "error", "message": "Learner state unavailable."}

    history = get_learning_history(user_id, limit=25).get("history", [])
    roadmap_summary = state.get("roadmap_summary", {})
    mastery = state.get("mastery", {})
    profile = state.get("profile", {})
    intervention = get_intervention_plan(user_id)

    assessment_scores = [
        _safe_float(item.get("score"), 0.0)
        for item in history
        if item.get("activity_type") in {"diagnostic", "checkpoint", "assessment", "quiz"}
        and item.get("score") is not None
    ]
    average_score = round(sum(assessment_scores) / len(assessment_scores), 3) if assessment_scores else None
    recent_topics = state.get("recent_topics", [])
    weak_topics = state.get("weak_topics", [])
    completed_sessions = _safe_int(roadmap_summary.get("completed_sessions"), 0)
    missed_sessions = _safe_int(roadmap_summary.get("missed_sessions"), 0)

    wins = []
    if completed_sessions:
        wins.append(f"Completed {completed_sessions} roadmap session(s).")
    if average_score is not None:
        wins.append(f"Average recent assessment score: {round(average_score * 100)}%.")
    if not wins:
        wins.append("The learner has started building a study record this week.")

    focus_next_week = []
    if weak_topics:
        focus_next_week.append(f"Prioritize remediation on {', '.join(weak_topics[:2])}.")
    if missed_sessions >= 2:
        focus_next_week.append("Use recovery mode with a shorter, high-focus roadmap.")
    if not focus_next_week:
        focus_next_week.append("Continue the current roadmap and add one checkpoint quiz.")

    report = {
        "status": "success",
        "title": f"ARKAIS Weekly Learning Report - {profile.get('topic') or state.get('current_topic') or 'Study Progress'}",
        "overview": {
            "current_topic": state.get("current_topic", ""),
            "overall_mastery_score": mastery.get("overall_score", 0.0),
            "overall_mastery_label": mastery.get("overall_label", "needs support"),
            "recent_topics": recent_topics,
            "completed_sessions": completed_sessions,
            "missed_sessions": missed_sessions,
            "average_assessment_score": average_score,
        },
        "wins": wins,
        "risks": intervention.get("triggers", []),
        "next_week_focus": focus_next_week,
        "recommended_actions": intervention.get("recommended_actions", []),
    }

    note_text = [
        report["title"],
        "",
        f"Current topic: {report['overview']['current_topic'] or 'Not set'}",
        f"Overall mastery: {round(_safe_float(report['overview']['overall_mastery_score']) * 100)}% ({report['overview']['overall_mastery_label']})",
        f"Completed sessions: {completed_sessions}",
        f"Missed sessions: {missed_sessions}",
    ]
    if average_score is not None:
        note_text.append(f"Average recent assessment score: {round(average_score * 100)}%")
    if recent_topics:
        note_text.append(f"Recent topics: {', '.join(recent_topics)}")
    if report["wins"]:
        note_text.extend(["", "Wins:"] + [f"- {item}" for item in report["wins"]])
    if report["risks"]:
        note_text.extend(["", "Risks:"] + [f"- {item}" for item in report["risks"]])
    if report["next_week_focus"]:
        note_text.extend(["", "Next week focus:"] + [f"- {item}" for item in report["next_week_focus"]])
    if report["recommended_actions"]:
        note_text.extend(["", "Recommended actions:"] + [f"- {item}" for item in report["recommended_actions"]])

    report["note_text"] = "\n".join(note_text)
    report["report_id"] = str(uuid.uuid4())
    report["created_at"] = _utc_now()

    db = get_firestore_client()
    if db:
        _user_reports_collection(db, user_id).document(report["report_id"]).set(report)
        _touch_user_doc(db, user_id)

    return report


def get_evaluation_snapshot(user_id: str) -> dict[str, Any]:
    state = get_learner_state(user_id)
    if state.get("status") != "success":
        return {"status": "error", "message": "Learner state unavailable."}

    mastery = state.get("mastery", {})
    roadmap_summary = state.get("roadmap_summary", {})
    history = get_learning_history(user_id, limit=20).get("history", [])
    assessment_count = sum(
        1 for item in history if item.get("activity_type") in {"diagnostic", "assessment", "checkpoint", "quiz"}
    )
    progress_count = len(history)
    grounding_available = False
    try:
        from materials import list_learning_materials

        grounding_available = bool(list_learning_materials(user_id).get("materials"))
    except Exception:
        grounding_available = False

    warnings = []
    if assessment_count == 0:
        warnings.append("No assessment data yet.")
    if not roadmap_summary.get("phase_count"):
        warnings.append("No roadmap generated yet.")
    if not grounding_available:
        warnings.append("No learner materials uploaded yet.")

    return {
        "status": "success",
        "coverage": {
            "assessment_count": assessment_count,
            "progress_events": progress_count,
            "roadmap_present": bool(roadmap_summary.get("phase_count")),
            "grounding_available": grounding_available,
        },
        "quality": {
            "overall_mastery_score": mastery.get("overall_score", 0.0),
            "completion_rate": roadmap_summary.get("completion_rate", 0.0),
            "missed_sessions": roadmap_summary.get("missed_sessions", 0),
        },
        "warnings": warnings,
    }


def get_learner_state(user_id: str) -> dict[str, Any]:
    profile_result = get_learner_profile(user_id)
    history_result = get_learning_history(user_id, limit=20)
    notes_result = list_study_notes(user_id, limit=5)
    mastery_result = get_mastery_snapshot(user_id)
    roadmap_result = get_roadmap(user_id)

    profile = profile_result if profile_result.get("status") == "success" else {}
    history = history_result.get("history", [])
    notes = notes_result.get("notes", [])
    mastery = mastery_result if mastery_result.get("status") == "success" else {"topics": [], "overall_score": 0.0}
    roadmap = roadmap_result.get("roadmap") if roadmap_result.get("status") == "success" else {}
    roadmap_summary = roadmap_result.get("summary") if roadmap_result.get("status") == "success" else {}

    recent_topics = [item.get("topic") for item in history if item.get("topic")]
    current_topic = profile.get("topic") or (recent_topics[0] if recent_topics else "")
    completed_activities = len(history)
    latest_activity = history[0] if history else {}
    weak_topics = [topic.get("topic", "") for topic in mastery.get("topics", []) if topic.get("score", 0.0) < 0.65][:3]

    recommended_next_action = "Take a short diagnostic and generate a roadmap."
    if roadmap_summary.get("missed_sessions", 0) >= 2:
        recommended_next_action = "Recovery roadmap is recommended because multiple sessions were missed."
    elif roadmap_summary.get("next_session", {}).get("title"):
        recommended_next_action = f"Next roadmap step: {roadmap_summary['next_session']['title']}."
    elif mastery.get("overall_score", 0.0) == 0 and current_topic:
        recommended_next_action = f"Start with a diagnostic on {current_topic}."
    elif weak_topics:
        recommended_next_action = f"Review {weak_topics[0]} with a short remedial lesson and quiz."
    elif current_topic:
        recommended_next_action = f"Continue with the next lesson on {current_topic}."

    return {
        "status": "success",
        "user_id": user_id,
        "profile": profile,
        "current_topic": current_topic,
        "completed_activities": completed_activities,
        "recent_history": history[:10],
        "recent_topics": recent_topics[:5],
        "weak_topics": weak_topics,
        "latest_activity": latest_activity,
        "saved_notes_count": len(notes),
        "mastery": mastery,
        "roadmap": roadmap,
        "roadmap_summary": roadmap_summary,
        "recommended_next_action": recommended_next_action,
    }


def describe_learner_state(user_id: str) -> str:
    state = get_learner_state(user_id)
    if state.get("status") != "success":
        return ""

    profile = state.get("profile", {})
    parts = []
    if profile.get("level"):
        parts.append(f"Level: {profile['level']}")
    if profile.get("learning_style"):
        parts.append(f"Learning style: {profile['learning_style']}")
    if profile.get("available_time"):
        parts.append(f"Daily study time: {profile['available_time']} minutes")
    if state.get("current_topic"):
        parts.append(f"Current topic: {state['current_topic']}")
    mastery = state.get("mastery", {})
    parts.append(f"Overall mastery: {mastery.get('overall_score', 0.0):.0%} ({mastery.get('overall_label', 'needs support')})")
    roadmap_summary = state.get("roadmap_summary", {})
    if roadmap_summary.get("phase_count"):
        parts.append(
            f"Roadmap: {roadmap_summary.get('mode', 'standard')} mode, "
            f"{roadmap_summary.get('completed_sessions', 0)}/{roadmap_summary.get('total_sessions', 0)} sessions completed"
        )
    if state.get("weak_topics"):
        parts.append(f"Weak topics: {', '.join(state['weak_topics'])}")
    if state.get("recommended_next_action"):
        parts.append(f"Recommended next action: {state['recommended_next_action']}")
    return "\n".join(parts)
