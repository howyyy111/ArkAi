import base64
import io
import json
import mimetypes
import os
import re
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import types
from firebase_admin import firestore

try:
    from .learner_state import create_custom_assessment, get_firestore_client
except ImportError:
    from learner_state import create_custom_assessment, get_firestore_client


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env", override=True)

SQLITE_DB_PATH = BASE_DIR / "learning_agent.db"
UPLOADS_DIR = BASE_DIR / "learner_uploads"
MATERIAL_MODEL = os.environ.get("ARKAIS_MATERIAL_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
MAX_MATERIAL_FILE_SIZE_BYTES = 5 * 1024 * 1024
MAX_MATERIAL_LIBRARY_SIZE_BYTES = 25 * 1024 * 1024

TEXT_EXTENSIONS = (
    ".md", ".txt", ".csv", ".tsv", ".json", ".py", ".js", ".html", ".css",
    ".xml", ".yaml", ".yml", ".java", ".c", ".cpp", ".cs", ".go", ".rs",
    ".rb", ".php", ".sql", ".log",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip()).strip("-")
    return cleaned[:120] or "material"


def _safe_user_folder(user_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9._@-]+", "_", str(user_id or "").strip())[:120] or "user"
    path = UPLOADS_DIR / safe
    path.mkdir(parents=True, exist_ok=True)
    return path


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


def _connect_sqlite() -> sqlite3.Connection:
    conn = sqlite3.connect(SQLITE_DB_PATH, timeout=30, check_same_thread=False)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass
    return conn


def init_materials_sqlite():
    conn = _connect_sqlite()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS learner_materials (
            material_id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT,
            mime_type TEXT,
            kind TEXT,
            local_path TEXT,
            source_type TEXT,
            extracted_text TEXT,
            summary TEXT,
            metadata_json TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def _material_collection(db, user_id: str):
    return db.collection("users").document(user_id).collection("materials")


def _decode_base64(data_base64: str) -> bytes:
    raw = str(data_base64 or "")
    if "," in raw and raw.split(",", 1)[0].startswith("data:"):
        raw = raw.split(",", 1)[1]
    return base64.b64decode(raw)


def _extract_text_from_pdf(blob: bytes) -> str:
    for module_name in ("pypdf", "PyPDF2"):
        try:
            module = __import__(module_name)
            reader = module.PdfReader(io.BytesIO(blob))
            page_text = [
                page.extract_text() or ""
                for page in reader.pages[:40]
            ]
            text = "\n\n".join(part.strip() for part in page_text if part.strip())
            if text:
                return text
        except Exception:
            continue

    try:
        decoded = blob.decode("latin-1", errors="ignore")
    except Exception:
        return ""
    literal_strings = re.findall(r"\(([^()]*)\)\s*Tj", decoded)
    array_strings = re.findall(r"\[((?:\([^()]*\)\s*)+)\]\s*TJ", decoded)
    parts = []
    for item in literal_strings:
        cleaned = item.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
        if cleaned.strip():
            parts.append(cleaned.strip())
    for group in array_strings:
        joined = "".join(re.findall(r"\(([^()]*)\)", group))
        if joined.strip():
            parts.append(joined.strip())
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _extract_text_from_image(blob: bytes, name: str) -> str:
    client = _get_genai_client()
    if not client:
        return ""
    try:
        with Image.open(io.BytesIO(blob)) as image:
            image_copy = image.copy()
        response = client.models.generate_content(
            model=MATERIAL_MODEL,
            contents=[
                (
                    "Extract the readable text and study-relevant content from this uploaded "
                    f"image named {name}. Return concise plain text only."
                ),
                image_copy,
            ],
            config=types.GenerateContentConfig(temperature=0.1),
        )
        return (response.text or "").strip()
    except Exception:
        return ""


def _extract_text_from_payload(name: str, mime_type: str, blob: bytes, pasted_text: str) -> str:
    if pasted_text:
        return pasted_text.strip()

    guessed_mime = mime_type or mimetypes.guess_type(name)[0] or ""
    lower_name = name.lower()
    if guessed_mime == "application/pdf" or lower_name.endswith(".pdf"):
        return _extract_text_from_pdf(blob)
    if guessed_mime.startswith("image/"):
        return _extract_text_from_image(blob, name)
    if guessed_mime.startswith("text/") or lower_name.endswith(TEXT_EXTENSIONS):
        try:
            return blob.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return blob.decode("latin-1")
            except UnicodeDecodeError:
                return ""
    return ""


def _build_summary(extracted_text: str, name: str) -> str:
    text = re.sub(r"\s+", " ", extracted_text or "").strip()
    if not text:
        return f"{name} uploaded successfully."
    preview = text[:280]
    if len(text) > 280:
        preview += "..."
    return preview


def _get_total_material_storage_bytes(user_id: str) -> int:
    records = _get_material_records(user_id)
    return sum(int((record.get("metadata") or {}).get("size_bytes", 0) or 0) for record in records)


def save_learning_material(
    user_id: str,
    name: str,
    mime_type: str = "",
    data_base64: str = "",
    pasted_text: str = "",
) -> dict[str, Any]:
    init_materials_sqlite()
    material_id = str(uuid.uuid4())
    created_at = _utc_now()
    clean_name = _safe_name(name or "material")
    blob = _decode_base64(data_base64) if data_base64 else pasted_text.encode("utf-8")
    
    if len(blob) > MAX_MATERIAL_FILE_SIZE_BYTES:
        return {"status": "error", "message": "File exceeds the 5 MB limit."}
    if _get_total_material_storage_bytes(user_id) + len(blob) > MAX_MATERIAL_LIBRARY_SIZE_BYTES:
        return {"status": "error", "message": "Library storage limit reached. Keep total materials under 25 MB."}

    mime = mime_type or mimetypes.guess_type(clean_name)[0] or "application/octet-stream"
    allowed_mimes = [
        "application/pdf", "text/plain", "text/csv", "application/json", 
        "application/javascript", "application/xml", "image/png", "image/jpeg", "image/webp"
    ]
    if not pasted_text and not mime.startswith("text/") and mime not in allowed_mimes and not clean_name.lower().endswith(TEXT_EXTENSIONS):
        return {"status": "error", "message": f"Unsupported file type: {mime}"}

    kind = "image" if mime.startswith("image/") else "text" if pasted_text or mime.startswith("text/") else "file"

    local_dir = _safe_user_folder(user_id)
    local_path = local_dir / f"{material_id}-{clean_name}"
    local_path.write_bytes(blob)

    extracted_text = _extract_text_from_payload(clean_name, mime, blob, pasted_text)
    metadata: dict[str, Any] = {"size_bytes": len(blob)}
    
    # Attempt to upload to Google Cloud Storage (Firebase Storage) if configured
    remote_url = ""
    try:
        from firebase_admin import storage
        bucket = storage.bucket()
        if bucket:
            blob_obj = bucket.blob(f"materials/{user_id}/{material_id}-{clean_name}")
            blob_obj.upload_from_string(blob, content_type=mime)
            remote_url = blob_obj.public_url
            metadata["gcs_path"] = blob_obj.name
    except Exception:
        pass

    if kind == "image":
        try:
            with Image.open(local_path) as image:
                metadata["width"], metadata["height"] = image.size
        except Exception:
            pass

    summary = _build_summary(extracted_text, clean_name)
    record = {
        "material_id": material_id,
        "user_id": user_id,
        "name": clean_name,
        "mime_type": mime,
        "kind": kind,
        "local_path": str(local_path),
        "remote_url": remote_url,
        "source_type": "paste" if pasted_text else "upload",
        "extracted_text": extracted_text[:50000],
        "summary": summary,
        "metadata": metadata,
        "created_at": created_at,
    }

    db = get_firestore_client()
    if db:
        is_anonymous = str(user_id).startswith("guest:")
        db.collection("users").document(user_id).set(
            {
                "user_id": user_id,
                "is_anonymous": is_anonymous,
                "updated_at": created_at,
                **(
                    {"expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()}
                    if is_anonymous
                    else {}
                ),
            },
            merge=True,
        )
        _material_collection(db, user_id).document(material_id).set(record)
        storage = "firestore+gcs" if remote_url else "firestore+localfile"
    else:
        conn = _connect_sqlite()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO learner_materials
            (material_id, user_id, name, mime_type, kind, local_path, source_type, extracted_text, summary, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                material_id,
                user_id,
                clean_name,
                mime,
                kind,
                str(local_path),
                "paste" if pasted_text else "upload",
                record["extracted_text"],
                summary,
                json.dumps(metadata),
                created_at,
            ),
        )
        conn.commit()
        conn.close()
        storage = "sqlite+localfile"

    return {
        "status": "success",
        "storage": storage,
        "material": {
            "material_id": material_id,
            "name": clean_name,
            "mime_type": mime,
            "kind": kind,
            "summary": summary,
            "created_at": created_at,
            "metadata": metadata,
        },
    }


def list_learning_materials(user_id: str) -> dict[str, Any]:
    db = get_firestore_client()
    if db:
        docs = (
            _material_collection(db, user_id)
            .order_by("created_at", direction=firestore.Query.DESCENDING)
            .stream()
        )
        materials = []
        for doc in docs:
            payload = doc.to_dict() or {}
            materials.append(
                {
                    "material_id": payload.get("material_id"),
                    "name": payload.get("name"),
                    "mime_type": payload.get("mime_type"),
                    "kind": payload.get("kind"),
                    "summary": payload.get("summary"),
                    "created_at": payload.get("created_at"),
                    "metadata": payload.get("metadata", {}),
                }
            )
        return {"status": "success", "materials": materials}

    init_materials_sqlite()
    conn = _connect_sqlite()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT material_id, name, mime_type, kind, summary, metadata_json, created_at
        FROM learner_materials
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    materials = [
        {
            "material_id": row[0],
            "name": row[1],
            "mime_type": row[2],
            "kind": row[3],
            "summary": row[4],
            "metadata": json.loads(row[5] or "{}"),
            "created_at": row[6],
        }
        for row in rows
    ]
    return {"status": "success", "materials": materials}


def delete_learning_material(user_id: str, material_id: str) -> dict[str, Any]:
    normalized_id = str(material_id or "").strip()
    if not normalized_id:
        return {"status": "error", "message": "Missing material id."}

    record = None
    db = get_firestore_client()
    if db:
        snapshot = _material_collection(db, user_id).document(normalized_id).get()
        if snapshot.exists:
            record = snapshot.to_dict() or {}
            _material_collection(db, user_id).document(normalized_id).delete()
    else:
        init_materials_sqlite()
        conn = _connect_sqlite()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT local_path FROM learner_materials
            WHERE user_id = ? AND material_id = ?
            """,
            (user_id, normalized_id),
        )
        row = cur.fetchone()
        if row:
            record = {"local_path": row[0]}
            cur.execute(
                """
                DELETE FROM learner_materials
                WHERE user_id = ? AND material_id = ?
                """,
                (user_id, normalized_id),
            )
            conn.commit()
        conn.close()

    local_path = Path(record.get("local_path", "")) if record else None
    if local_path and local_path.is_file():
        try:
            local_path.unlink()
        except OSError:
            pass

    if not record:
        return {"status": "error", "message": "Material not found."}

    return {"status": "success", "message": "Material deleted.", "material_id": normalized_id}


def delete_all_learning_materials(user_id: str) -> dict[str, Any]:
    records = _get_material_records(user_id)
    if not records:
        return {"status": "success", "message": "No materials to delete.", "deleted_count": 0}

    db = get_firestore_client()
    if db:
        for record in records:
            material_id = str(record.get("material_id", "")).strip()
            if material_id:
                _material_collection(db, user_id).document(material_id).delete()
    else:
        init_materials_sqlite()
        conn = _connect_sqlite()
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM learner_materials
            WHERE user_id = ?
            """,
            (user_id,),
        )
        conn.commit()
        conn.close()

    deleted_count = 0
    for record in records:
        local_path = Path(record.get("local_path", ""))
        if local_path.is_file():
            try:
                local_path.unlink()
            except OSError:
                pass
        deleted_count += 1

    return {
        "status": "success",
        "message": "All materials deleted.",
        "deleted_count": deleted_count,
    }


def _get_material_records(user_id: str, material_ids: list[str] | None = None) -> list[dict[str, Any]]:
    wanted = set(material_ids or [])
    db = get_firestore_client()
    records: list[dict[str, Any]] = []
    if db:
        stream = _material_collection(db, user_id).stream()
        for doc in stream:
            payload = doc.to_dict() or {}
            if wanted and payload.get("material_id") not in wanted:
                continue
            records.append(payload)
        return records

    init_materials_sqlite()
    conn = _connect_sqlite()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT material_id, name, mime_type, kind, local_path, source_type, extracted_text, summary, metadata_json, created_at
        FROM learner_materials
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()
    for row in rows:
        if wanted and row[0] not in wanted:
            continue
        records.append(
            {
                "material_id": row[0],
                "name": row[1],
                "mime_type": row[2],
                "kind": row[3],
                "local_path": row[4],
                "source_type": row[5],
                "extracted_text": row[6],
                "summary": row[7],
                "metadata": json.loads(row[8] or "{}"),
                "created_at": row[9],
            }
        )
    return records


def build_material_context(user_id: str, query: str, material_ids: list[str] | None = None, limit: int = 3) -> dict[str, Any]:
    records = _get_material_records(user_id, material_ids)
    query_terms = [term for term in re.findall(r"[a-zA-Z0-9]+", (query or "").lower()) if len(term) > 2]
    ranked = []
    for record in records:
        haystack = f"{record.get('name', '')}\n{record.get('summary', '')}\n{record.get('extracted_text', '')}".lower()
        score = sum(haystack.count(term) for term in query_terms) if query_terms else 1
        if score <= 0 and query_terms:
            continue
        ranked.append((score, record))
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = [record for _, record in ranked[:limit]] or records[:limit]

    snippets = []
    sources = []
    for record in selected:
        text = re.sub(r"\s+", " ", record.get("extracted_text", "")).strip()
        snippet = text[:260] + ("..." if len(text) > 260 else "") if text else record.get("summary", "")
        snippets.append(f"Source: {record.get('name')} | Snippet: {snippet}")
        sources.append(
            {
                "material_id": record.get("material_id"),
                "name": record.get("name"),
                "kind": record.get("kind"),
            }
        )
    return {
        "status": "success",
        "context_text": "\n".join(snippets).strip(),
        "sources": sources,
    }


def tutor_from_materials(user_id: str, query: str, material_ids: list[str] | None = None) -> dict[str, Any]:
    records = _get_material_records(user_id, material_ids)
    if not records:
        return {"status": "error", "message": "No materials found to tutor from."}

    text_records = [record for record in records if record.get("extracted_text")]
    image_records = [record for record in records if record.get("kind") == "image"]
    client = _get_genai_client()

    if client:
        contents: list[Any] = []
        prompt_parts = [
            "Answer the learner's question using only the provided materials when possible.",
            "Be concise and include a short Sources section naming the materials you relied on.",
            f"Question: {query}",
        ]
        if text_records:
            joined = "\n\n".join(
                f"{record.get('name')}:\n{record.get('extracted_text', '')[:6000]}"
                for record in text_records[:3]
            )
            prompt_parts.append(f"Text materials:\n{joined}")
        contents.append("\n\n".join(prompt_parts))
        for record in image_records[:2]:
            path = Path(record.get("local_path", ""))
            if path.is_file():
                try:
                    with Image.open(path) as image:
                        contents.append(image.copy())
                except Exception:
                    continue
        try:
            response = client.models.generate_content(
                model=MATERIAL_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.3),
            )
            answer = (response.text or "").strip()
            if answer:
                return {
                    "status": "success",
                    "answer": answer,
                    "sources": [{"material_id": record.get("material_id"), "name": record.get("name")} for record in records[:4]],
                }
        except Exception:
            pass

    context = build_material_context(user_id, query, material_ids, limit=3)
    answer_lines = ["Here’s a grounded answer from your uploaded materials:"]
    if context.get("context_text"):
        answer_lines.append(context["context_text"])
    if image_records:
        image_notes = [
            f"{record.get('name')} ({record.get('metadata', {}).get('width', '?')}x{record.get('metadata', {}).get('height', '?')})"
            for record in image_records[:2]
        ]
        answer_lines.append("Image materials available: " + ", ".join(image_notes))
    answer_lines.append("Sources: " + ", ".join(source["name"] for source in context.get("sources", [])))
    return {
        "status": "success",
        "answer": "\n\n".join(answer_lines),
        "sources": context.get("sources", []),
    }


def create_mock_test_from_materials(
    user_id: str,
    material_ids: list[str] | None = None,
    topic: str = "",
    level: str = "beginner",
    goal: str = "",
    question_count: int = 5,
    structure: str = "",
    sample_style: str = "",
) -> dict[str, Any]:
    records = _get_material_records(user_id, material_ids)
    if not records:
        return {"status": "error", "message": "No materials found to build a mock test from."}

    try:
        question_count = max(3, min(7, int(question_count)))
    except (TypeError, ValueError):
        question_count = 5

    text_records = [record for record in records if record.get("extracted_text")]
    if not text_records:
        return {"status": "error", "message": "These materials do not contain enough text for a mock test yet."}

    topic_name = str(topic).strip() or Path(text_records[0].get("name", "uploaded material")).stem.replace("-", " ")
    client = _get_genai_client()
    if not client:
        return {"status": "error", "message": "Mock test generation is unavailable right now."}

    joined = "\n\n".join(
        f"{record.get('name')}:\n{record.get('extracted_text', '')[:7000]}"
        for record in text_records[:3]
    )
    prompt = f"""
Create a mock test using only the learner materials below.

Topic: {topic_name}
Level: {level}
Goal: {goal or "Check real understanding from the uploaded notes"}
Question count: {question_count}
Requested structure: {structure or "Balanced exam with a mix of question types"}
Sample exam style: {sample_style or "No sample style provided"}

Materials:
{joined}

Return JSON only with this shape:
{{
  "questions": [
    {{
      "question_type": "multiple_choice or short_answer or essay",
      "prompt": "Question text",
      "options": ["A option", "B option", "C option", "D option"],
      "correct_answer": "A or a short expected answer",
      "explanation": "Short explanation grounded in the material",
      "concept": "short concept tag",
      "difficulty": "{level}",
      "grading_guide": "What a strong answer should include"
    }}
  ]
}}

Requirements:
- Use only the uploaded material.
- Make the questions feel like a real mock test, not trivia.
- Follow the requested structure and sample style closely when they are provided.
- Include a mix of multiple choice, short answer, and essay when the structure suggests it.
- Cover different ideas from the material where possible.
- Keep wording simple and clear.
- For multiple_choice, return exactly 4 options.
- For short_answer and essay, return an empty options array.
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
                        "question_type": {"type": "string"},
                        "options": {
                            "type": "array",
                            "minItems": 0,
                            "maxItems": 4,
                            "items": {"type": "string"},
                        },
                        "correct_answer": {"type": "string"},
                        "explanation": {"type": "string"},
                        "concept": {"type": "string"},
                        "difficulty": {"type": "string"},
                        "grading_guide": {"type": "string"},
                    },
                    "required": ["prompt", "question_type", "options", "correct_answer", "explanation", "concept", "difficulty", "grading_guide"],
                },
            }
        },
        "required": ["questions"],
    }

    try:
        response = client.models.generate_content(
            model=MATERIAL_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                responseMimeType="application/json",
                responseSchema=schema,
            ),
        )
        payload = json.loads(response.text)
        questions = payload.get("questions") or []
    except Exception as exc:
        return {"status": "error", "message": f"Could not generate mock test: {exc}"}

    assessment = create_custom_assessment(
        user_id=user_id,
        topic=topic_name,
        questions=questions,
        assessment_type="mock_test",
        level=level,
        goal=goal or f"Mock test from uploaded materials: {topic_name}",
    )
    if assessment.get("status") != "success":
        return assessment

    assessment["sources"] = [
        {"material_id": record.get("material_id"), "name": record.get("name")}
        for record in records[:4]
    ]
    assessment["message"] = "Mock test created from your materials."
    return assessment
