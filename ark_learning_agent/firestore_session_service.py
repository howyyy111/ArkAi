import copy
import uuid
from typing import Any, Optional

from google.adk.events import Event
from google.adk.sessions import BaseSessionService, Session
from google.adk.sessions.base_session_service import GetSessionConfig, ListSessionsResponse

try:
    from .learner_state import get_firestore_client
except ImportError:
    from learner_state import get_firestore_client


class FirestoreSessionService(BaseSessionService):
    """Stores ADK sessions and events in Firestore under users/{uid}/chat_sessions."""

    def __init__(self) -> None:
        self._db = get_firestore_client()

    def is_available(self) -> bool:
        return self._db is not None

    def _session_doc(self, app_name: str, user_id: str, session_id: str):
        return (
            self._db.collection("users")
            .document(user_id)
            .collection("chat_sessions")
            .document(session_id)
        )

    def _event_collection(self, app_name: str, user_id: str, session_id: str):
        return self._session_doc(app_name, user_id, session_id).collection("events")

    def _extract_adk_session_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = dict((data.get("adk_session") or {}))
        if payload:
            return payload

        # Browser session metadata shares the same document path. Treat a
        # metadata-only document as "no ADK session yet" instead of returning a
        # Session object with an empty id.
        fallback = {
            "id": data.get("id"),
            "app_name": data.get("app_name"),
            "user_id": data.get("user_id"),
            "state": data.get("state"),
            "last_update_time": data.get("last_update_time"),
        }
        if fallback["id"] and fallback["app_name"] and fallback["user_id"]:
            return fallback
        return {}

    def _serialize_session(self, session: Session) -> dict[str, Any]:
        return {
            "id": session.id,
            "app_name": session.app_name,
            "user_id": session.user_id,
            "state": session.state,
            "last_update_time": session.last_update_time,
            "updated_at": session.last_update_time,
            "adk_session": {
                "id": session.id,
                "app_name": session.app_name,
                "user_id": session.user_id,
                "state": session.state,
                "last_update_time": session.last_update_time,
            },
        }

    def _deserialize_session(
        self,
        data: dict[str, Any],
        events: Optional[list[Event]] = None,
    ) -> Session:
        session_payload = self._extract_adk_session_payload(data)
        return Session(
            id=str(session_payload.get("id") or ""),
            app_name=str(session_payload.get("app_name") or ""),
            user_id=str(session_payload.get("user_id") or ""),
            state=dict(session_payload.get("state") or {}),
            events=events or [],
            last_update_time=float(session_payload.get("last_update_time") or 0.0),
        )

    def _serialize_event(self, event: Event) -> dict[str, Any]:
        payload = event.model_dump(mode="json", by_alias=False)
        payload["timestamp"] = event.timestamp
        payload["id"] = event.id
        return payload

    def _deserialize_event(self, data: dict[str, Any]) -> Event:
        return Event.model_validate(data)

    def _create_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        if not self._db:
            raise RuntimeError("Firestore session service is unavailable.")

        if session_id and self._get_session_impl(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
        ):
            raise ValueError(f"Session with id {session_id} already exists.")

        session = Session(
            id=str(session_id).strip() if session_id and str(session_id).strip() else str(uuid.uuid4()),
            app_name=app_name,
            user_id=user_id,
            state=copy.deepcopy(state or {}),
            events=[],
            last_update_time=0.0,
        )
        self._session_doc(app_name, user_id, session.id).set(
            self._serialize_session(session),
            merge=True,
        )
        return copy.deepcopy(session)

    def _get_session_impl(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        if not self._db:
            return None

        snapshot = self._session_doc(app_name, user_id, session_id).get()
        if not snapshot.exists:
            return None

        raw_data = snapshot.to_dict() or {}
        session_payload = self._extract_adk_session_payload(raw_data)
        if not session_payload:
            return None

        docs = self._event_collection(app_name, user_id, session_id).order_by("timestamp").stream()
        events = [self._deserialize_event(doc.to_dict() or {}) for doc in docs]
        session = self._deserialize_session(raw_data, events=events)

        if config:
            if config.num_recent_events:
                session.events = session.events[-config.num_recent_events :]
            if config.after_timestamp is not None:
                session.events = [
                    event for event in session.events
                    if float(event.timestamp) >= float(config.after_timestamp)
                ]

        return copy.deepcopy(session)

    def _list_sessions_impl(
        self,
        *,
        app_name: str,
        user_id: Optional[str] = None,
    ) -> ListSessionsResponse:
        if not self._db:
            return ListSessionsResponse()

        sessions: list[Session] = []
        if user_id is None:
            user_docs = self._db.collection("users").stream()
            for user_doc in user_docs:
                uid = user_doc.id
                session_docs = (
                    self._db.collection("users")
                    .document(uid)
                    .collection("chat_sessions")
                    .where("app_name", "==", app_name)
                    .stream()
                )
                for doc in session_docs:
                    sessions.append(self._deserialize_session(doc.to_dict() or {}, events=[]))
        else:
            session_docs = (
                self._db.collection("users")
                .document(user_id)
                .collection("chat_sessions")
                .where("app_name", "==", app_name)
                .stream()
            )
            for doc in session_docs:
                sessions.append(self._deserialize_session(doc.to_dict() or {}, events=[]))

        for session in sessions:
            session.events = []
            session.state = {}
        return ListSessionsResponse(sessions=sessions)

    def _delete_session_impl(self, *, app_name: str, user_id: str, session_id: str) -> None:
        if not self._db:
            return

        for event_doc in self._event_collection(app_name, user_id, session_id).stream():
            event_doc.reference.delete()
        self._session_doc(app_name, user_id, session_id).delete()

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        return self._create_session_impl(
            app_name=app_name,
            user_id=user_id,
            state=state,
            session_id=session_id,
        )

    def create_session_sync(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        return self._create_session_impl(
            app_name=app_name,
            user_id=user_id,
            state=state,
            session_id=session_id,
        )

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        return self._get_session_impl(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            config=config,
        )

    def get_session_sync(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        return self._get_session_impl(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            config=config,
        )

    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        return self._list_sessions_impl(app_name=app_name, user_id=user_id)

    def list_sessions_sync(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        return self._list_sessions_impl(app_name=app_name, user_id=user_id)

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        self._delete_session_impl(app_name=app_name, user_id=user_id, session_id=session_id)

    def delete_session_sync(self, *, app_name: str, user_id: str, session_id: str) -> None:
        self._delete_session_impl(app_name=app_name, user_id=user_id, session_id=session_id)

    async def append_event(self, session: Session, event: Event) -> Event:
        if not self._db:
            return await super().append_event(session=session, event=event)

        event = await super().append_event(session=session, event=event)
        self._event_collection(session.app_name, session.user_id, session.id).document(event.id).set(
            self._serialize_event(event)
        )
        self._session_doc(session.app_name, session.user_id, session.id).set(
            self._serialize_session(session),
            merge=True,
        )
        return event
