import os
import tempfile
import unittest
from unittest import mock


os.environ["ARKAIS_FORCE_SQLITE"] = "1"
os.environ.pop("K_SERVICE", None)

import frontend_server
from ark_learning_agent.firestore_session_service import FirestoreSessionService
from ark_learning_agent import frontend_api
from ark_learning_agent import learner_state
from ark_learning_agent import productivity_mcp_server
from ark_learning_agent import web_session_store
from google.adk.sessions import Session


class FrontendServerTests(unittest.TestCase):
    def make_handler(self, cookie_header: str = "", path: str = "/api/session"):
        handler = object.__new__(frontend_server.ArkAisHandler)
        handler.headers = {"Cookie": cookie_header} if cookie_header else {}
        handler._pending_cookies = []
        handler.path = path
        return handler

    def test_persistent_sessions_required_in_cloud_run(self):
        with mock.patch.dict(os.environ, {"K_SERVICE": "frontend"}, clear=False):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("ARKAIS_ALLOW_IN_MEMORY_SESSIONS", None)
                self.assertTrue(frontend_server._persistent_session_backend_required())

    def test_persistent_sessions_can_be_relaxed_explicitly(self):
        with mock.patch.dict(
            os.environ,
            {"K_SERVICE": "frontend", "ARKAIS_ALLOW_IN_MEMORY_SESSIONS": "1"},
            clear=False,
        ):
            self.assertFalse(frontend_server._persistent_session_backend_required())

    def test_validate_session_backend_warns_when_production_lacks_firestore(self):
        backend = mock.Mock()
        with mock.patch.object(
            frontend_server,
            "_persistent_session_backend_required",
            return_value=True,
        ):
            with self.assertLogs(frontend_server.LOGGER, level="WARNING") as logs:
                frontend_server._validate_session_backend_or_raise(backend)
        self.assertTrue(
            any("Persistent Firestore-backed sessions are unavailable" in entry for entry in logs.output)
        )

    def test_system_status_uses_callback_url_from_credentials_when_env_missing(self):
        with mock.patch.object(frontend_server, "_resolved_auth_callback_url", return_value="https://example.com/auth"):
            status = frontend_server._system_status()

        self.assertTrue(status["readiness"]["auth_callback_configured"])
        self.assertEqual(status["integrations"]["auth_callback_url"], "https://example.com/auth")

    def test_resolve_authenticated_user_prefers_session_cookie(self):
        headers = {"Cookie": f"{frontend_server.FIREBASE_SESSION_COOKIE_NAME}=secure-cookie"}
        with mock.patch.object(frontend_server, "_firebase_admin_app"):
            with mock.patch.object(
                frontend_server.firebase_auth,
                "verify_session_cookie",
                return_value={"email": "person@example.com"},
            ) as verify_session_cookie:
                with mock.patch.object(frontend_server.firebase_auth, "verify_id_token") as verify_id_token:
                    user_id, token = frontend_server._resolve_authenticated_user({}, headers)

        self.assertEqual(user_id, "person@example.com")
        self.assertEqual(token, "secure-cookie")
        verify_session_cookie.assert_called_once()
        verify_id_token.assert_not_called()

    def test_resolve_authenticated_user_allows_email_fallback_without_firebase_config(self):
        with mock.patch.object(frontend_server, "_firebase_web_config", return_value=None):
            user_id, token = frontend_server._resolve_authenticated_user(
                {"userId": "Person@Example.com"},
                {},
            )

        self.assertEqual(user_id, "person@example.com")
        self.assertEqual(token, "email_fallback")

    def test_resolve_authenticated_user_ignores_email_fallback_when_firebase_configured(self):
        firebase_config = {
            "apiKey": "key",
            "authDomain": "example.firebaseapp.com",
            "projectId": "project",
            "appId": "app",
        }
        with mock.patch.object(frontend_server, "_firebase_web_config", return_value=firebase_config):
            user_id, token = frontend_server._resolve_authenticated_user(
                {"userId": "person@example.com"},
                {},
            )

        self.assertEqual(user_id, "")
        self.assertEqual(token, "")

    def test_resolve_request_context_uses_cookie_identity_and_session(self):
        handler = self.make_handler(
            f"{frontend_server.CLIENT_COOKIE_NAME}=client-123; "
            f"{frontend_server.SESSION_COOKIE_NAME}=session-456"
        )
        with mock.patch.object(
            frontend_server,
            "_resolve_authenticated_user",
            return_value=("user@example.com", "token"),
        ):
            with mock.patch.object(
                frontend_server,
                "get_or_create_browser_identity",
                return_value={
                    "client_id": "client-123",
                    "user_id": "user@example.com",
                    "is_authenticated": True,
                },
            ) as get_identity:
                with mock.patch.object(
                    frontend_server,
                    "get_or_create_chat_session",
                    return_value={
                        "session_id": "session-456",
                        "client_id": "client-123",
                        "user_id": "user@example.com",
                    },
                ) as get_session:
                    context = handler._resolve_request_context()

        self.assertEqual(context["user_id"], "user@example.com")
        self.assertEqual(context["session_id"], "session-456")
        get_identity.assert_called_once_with(
            client_id="client-123",
            authenticated_user_id="user@example.com",
            reset_identity=False,
        )
        get_session.assert_called_once_with(
            client_id="client-123",
            user_id="user@example.com",
            session_id="session-456",
            reset_session=False,
        )

    def test_resolve_request_context_can_ignore_auth_for_logout(self):
        handler = self.make_handler()
        with mock.patch.object(
            frontend_server,
            "_resolve_authenticated_user",
            side_effect=AssertionError("auth should be skipped"),
        ):
            with mock.patch.object(
                frontend_server,
                "get_or_create_browser_identity",
                return_value={
                    "client_id": "client-guest",
                    "user_id": "guest:abc123",
                    "is_authenticated": False,
                },
            ):
                with mock.patch.object(
                    frontend_server,
                    "get_or_create_chat_session",
                    return_value={
                        "session_id": "session-guest",
                        "client_id": "client-guest",
                        "user_id": "guest:abc123",
                    },
                ):
                    context = handler._resolve_request_context(ignore_auth=True)

        self.assertEqual(context["user_id"], "guest:abc123")
        self.assertTrue(context["is_anonymous"])

    def test_resolve_request_context_uses_query_user_for_email_fallback_gets(self):
        handler = self.make_handler(path="/api/learner-state?userId=Person%40Example.com")
        with mock.patch.object(frontend_server, "_firebase_web_config", return_value=None):
            with mock.patch.object(
                frontend_server,
                "get_or_create_browser_identity",
                return_value={
                    "client_id": "client-123",
                    "user_id": "person@example.com",
                    "is_authenticated": True,
                },
            ) as get_identity:
                with mock.patch.object(
                    frontend_server,
                    "get_or_create_chat_session",
                    return_value={
                        "session_id": "session-123",
                        "client_id": "client-123",
                        "user_id": "person@example.com",
                    },
                ):
                    context = handler._resolve_request_context()

        self.assertEqual(context["user_id"], "person@example.com")
        self.assertFalse(context["is_anonymous"])
        get_identity.assert_called_once_with(
            client_id="",
            authenticated_user_id="person@example.com",
            reset_identity=False,
        )

    def test_guest_user_payload_includes_expiry(self):
        payload = web_session_store._user_doc_payload("guest:abc123", now="2026-01-01T00:00:00+00:00")
        self.assertTrue(payload["is_anonymous"])
        self.assertIn("expires_at", payload)

    def test_signed_in_user_payload_has_no_expiry(self):
        payload = web_session_store._user_doc_payload("person@example.com", now="2026-01-01T00:00:00+00:00")
        self.assertFalse(payload["is_anonymous"])
        self.assertNotIn("expires_at", payload)

    def test_google_status_rejects_legacy_access_token_without_expiry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            token_dir = os.path.join(tmpdir, "tokens")
            os.makedirs(token_dir, exist_ok=True)
            token_path = os.path.join(token_dir, "person@example.com.json")
            with open(token_path, "w", encoding="utf-8") as handle:
                handle.write('{"token": "legacy-token", "scopes": ["https://www.googleapis.com/auth/drive.file"]}')

            with mock.patch.object(productivity_mcp_server, "USER_GOOGLE_TOKENS_DIR", productivity_mcp_server.Path(token_dir)):
                status = productivity_mcp_server.google_oauth_status("person@example.com")

        self.assertFalse(status["connected"])

    def test_google_access_token_persist_includes_default_expiry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            token_dir = os.path.join(tmpdir, "tokens")
            with mock.patch.object(productivity_mcp_server, "USER_GOOGLE_TOKENS_DIR", productivity_mcp_server.Path(token_dir)):
                result = productivity_mcp_server.persist_google_access_token("person@example.com", "token-value")
                token_path = os.path.join(token_dir, "person@example.com.json")
                with open(token_path, encoding="utf-8") as handle:
                    payload = handle.read()

        self.assertEqual(result["status"], "success")
        self.assertIn('"expiry"', payload)

    def test_firestore_session_service_namespaces_adk_payload(self):
        service = FirestoreSessionService()
        session = Session(
            id="session-1",
            app_name="app",
            user_id="user@example.com",
            state={"key": "value"},
            events=[],
            last_update_time=123.0,
        )
        payload = service._serialize_session(session)
        self.assertIn("adk_session", payload)
        self.assertEqual(payload["adk_session"]["state"], {"key": "value"})
        restored = service._deserialize_session(payload, events=[])
        self.assertEqual(restored.id, "session-1")
        self.assertEqual(restored.state, {"key": "value"})

    def test_firestore_session_service_ignores_metadata_only_chat_session_docs(self):
        service = FirestoreSessionService()
        metadata_only_payload = {
            "session_id": "session-1",
            "client_id": "client-1",
            "user_id": "user@example.com",
            "created_at": "2026-01-01T00:00:00+00:00",
        }

        self.assertEqual(service._extract_adk_session_payload(metadata_only_payload), {})

    def test_firestore_session_service_accepts_legacy_top_level_adk_fields(self):
        service = FirestoreSessionService()
        legacy_payload = {
            "id": "session-legacy",
            "app_name": "app",
            "user_id": "user@example.com",
            "state": {"topic": "loops"},
            "last_update_time": 456.0,
        }

        restored = service._deserialize_session(legacy_payload, events=[])
        self.assertEqual(restored.id, "session-legacy")
        self.assertEqual(restored.app_name, "app")
        self.assertEqual(restored.user_id, "user@example.com")
        self.assertEqual(restored.state, {"topic": "loops"})

    def test_sqlite_chat_history_lists_and_loads_messages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "web_sessions.db")
            with mock.patch.object(web_session_store, "SQLITE_DB_PATH", web_session_store.Path(db_path)):
                identity = web_session_store.get_or_create_browser_identity(reset_identity=True)
                session = web_session_store.get_or_create_chat_session(
                    client_id=identity["client_id"],
                    user_id=identity["user_id"],
                )
                web_session_store.append_chat_message(
                    user_id=identity["user_id"],
                    session_id=session["session_id"],
                    role="user",
                    author="user",
                    content="Teach me binary search.",
                )
                web_session_store.append_chat_message(
                    user_id=identity["user_id"],
                    session_id=session["session_id"],
                    role="assistant",
                    author="ARKAI",
                    content="Binary search halves the search space each step.",
                )

                sessions = web_session_store.list_chat_sessions(identity["user_id"])
                messages = web_session_store.get_chat_messages(identity["user_id"], session["session_id"])
                delete_result = web_session_store.delete_all_chat_sessions(identity["user_id"])
                sessions_after_delete = web_session_store.list_chat_sessions(identity["user_id"])

        self.assertEqual(sessions["status"], "success")
        self.assertEqual(len(sessions["sessions"]), 1)
        self.assertEqual(sessions["sessions"][0]["title"], "Teach me binary search.")
        self.assertEqual(messages["status"], "success")
        self.assertEqual([message["role"] for message in messages["messages"]], ["user", "agent"])
        self.assertEqual(delete_result["status"], "success")
        self.assertEqual(sessions_after_delete["sessions"], [])

    def test_google_doc_formatter_uses_latest_prompt_and_answer(self):
        messages = [
            {"role": "user", "content": "Teach me binary search."},
            {"role": "agent", "content": "Binary search halves the search space each step."},
            {"role": "user", "content": "save this to google docs"},
        ]

        formatted = frontend_server._format_chat_messages_for_google_doc(messages)

        self.assertIn("ArkAI Tutor Notes", formatted)
        self.assertIn("Prompt\nTeach me binary search.", formatted)
        self.assertIn("Tutor response\nBinary search halves the search space each step.", formatted)
        self.assertNotIn("save this to google docs", formatted.lower())

    def test_google_destination_formatters_are_purpose_specific(self):
        long_answer = "Use a sorted array. " * 250
        messages = [
            {"role": "user", "content": "Explain binary search and give me practice."},
            {"role": "agent", "content": long_answer},
            {"role": "user", "content": "save in google calendar tomorrow at 9am"},
        ]

        drive_text = frontend_server._format_chat_messages_for_google_drive(messages)
        task_notes = frontend_server._format_chat_messages_for_google_task(messages)
        calendar_description = frontend_server._format_chat_messages_for_google_calendar(messages)

        self.assertTrue(drive_text.startswith("# ArkAI Tutor Notes"))
        self.assertIn("## Prompt", drive_text)
        self.assertIn("Created from ArkAI Tutor.", task_notes)
        self.assertLessEqual(len(task_notes), 3200)
        self.assertIn("ArkAI Tutor study session.", calendar_description)
        self.assertLessEqual(len(calendar_description), 1700)
        self.assertNotIn("save in google calendar", calendar_description.lower())

    def test_roadmap_calendar_sync_uses_session_due_dates(self):
        roadmap = {
            "phases": [
                {
                    "title": "Foundation 1",
                    "goal": "Practice loops",
                    "sessions": [
                        {
                            "title": "Loops session 1",
                            "focus": "for loops",
                            "duration_minutes": 45,
                            "status": "planned",
                            "due_date": "2026-05-03",
                        },
                        {
                            "title": "Loops session 2",
                            "focus": "while loops",
                            "duration_minutes": 30,
                            "status": "completed",
                            "due_date": "2026-05-04",
                        },
                    ],
                }
            ]
        }

        async def run_sync():
            with mock.patch(
                "ark_learning_agent.productivity_mcp_server.google_oauth_status",
                return_value={"connected": True},
            ), mock.patch(
                "ark_learning_agent.productivity_mcp_server.create_calendar_event",
                return_value={"status": "success", "message": "ok"},
            ) as create_event:
                result = await frontend_api._save_roadmap_result_to_google_calendar(
                    user_id="learner@example.com",
                    roadmap=roadmap,
                    timezone_name="Asia/Bangkok",
                    calendar_start_time="10:15",
                )
                return result, create_event

        result, create_event = __import__("asyncio").run(run_sync())

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["created_sessions"], ["Loops session 1"])
        create_event.assert_called_once()
        kwargs = create_event.call_args.kwargs
        self.assertEqual(kwargs["start_time_iso"], "2026-05-03T10:15:00+07:00")
        self.assertEqual(kwargs["end_time_iso"], "2026-05-03T11:00:00+07:00")
        self.assertNotIn("Focus:", kwargs["description"])

    def test_prompt_like_topics_fall_back_to_real_study_topic(self):
        self.assertEqual(
            learner_state._infer_learning_focus("Can you summarize that", "Environmental Science"),
            "Environmental Science",
        )
        phases = learner_state._build_roadmap_phases(
            topic="Environmental Science",
            goal="Prepare for exam",
            level="beginner",
            available_time=45,
            deadline_days=7,
            weak_topics=["Can you summarize that"],
            recovery_mode=False,
            start_date="2026-05-01",
        )

        first_session = phases[0]["sessions"][0]
        self.assertEqual(first_session["focus"], "Environmental Science")
        self.assertEqual(first_session["title"], "Environmental Science session 1")

    def test_completing_session_does_not_rebuild_standard_roadmap(self):
        roadmap = {
            "roadmap_id": "roadmap-1",
            "topic": "Trigonometry",
            "goal": "Final exam",
            "level": "advanced",
            "available_time": 45,
            "deadline_days": 7,
            "mode": "standard",
            "status": "active",
            "phases": learner_state._build_roadmap_phases(
                topic="Trigonometry",
                goal="Final exam",
                level="advanced",
                available_time=45,
                deadline_days=7,
                weak_topics=[],
                recovery_mode=False,
                start_date="2026-05-01",
            ),
        }

        with mock.patch.object(learner_state, "_load_roadmap", return_value=roadmap), \
             mock.patch.object(learner_state, "_save_roadmap"), \
             mock.patch.object(learner_state, "save_learning_progress"), \
             mock.patch.object(
                 learner_state,
                 "get_mastery_snapshot",
                 return_value={"topics": [{"topic": "Trigonometry", "score": 0.2}]},
             ):
            result = learner_state.update_roadmap_session(
                user_id="learner@example.com",
                phase_id="phase-1",
                session_id="phase-1-session-1",
                status="completed",
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summary"]["total_sessions"], 6)
        self.assertEqual(result["roadmap"]["mode"], "standard")


if __name__ == "__main__":
    unittest.main()
