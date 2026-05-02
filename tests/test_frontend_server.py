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
from ark_learning_agent import materials
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

    def test_google_credentials_without_expiry_and_refresh_token_need_refresh(self):
        creds = productivity_mcp_server.Credentials(
            token="old-token",
            refresh_token="refresh-token",
            token_uri="https://oauth2.googleapis.com/token",
            client_id="client-id",
            client_secret="client-secret",
            scopes=productivity_mcp_server.SCOPES,
        )

        self.assertTrue(productivity_mcp_server._credentials_need_refresh(creds))

    def test_google_api_permission_error_requests_reconnect(self):
        response = mock.Mock(status=403, reason="Forbidden")
        error = productivity_mcp_server.HttpError(response, b'{"error":"insufficientPermissions"}')

        result = productivity_mcp_server._google_api_failure_response(error)

        self.assertEqual(result["status"], "auth_required")
        self.assertIn("Reconnect Google saves", result["message"])

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

        formatted = frontend_api._format_chat_messages_for_google_doc(messages)

        self.assertIn("ArkAI Lecture Notes: Binary Search", formatted)
        self.assertIn("Binary search halves the search space each step.", formatted)
        self.assertNotIn("Prompt\nTeach me binary search.", formatted)
        self.assertNotIn("Tutor response", formatted)
        self.assertNotIn("save this to google docs", formatted.lower())

    def test_google_doc_formatter_removes_chatty_exercise_text_from_lecture_notes(self):
        messages = [
            {
                "role": "user",
                "content": (
                    "Teach me this roadmap session now: Environmental Science session 1. "
                    "Topic: Environmental Science. Give me a short explanation, one example, and one small exercise."
                ),
            },
            {
                "role": "agent",
                "content": (
                    "Let's start with your Environmental Science session 1!\n\n"
                    "What is Environmental Science?\n\n"
                    "Environmental Science studies how humans and nature interact.\n\n"
                    "Small Exercise:\n\n"
                    "Name one positive and one negative human impact.\n\n"
                    "Take a moment to think about it!"
                ),
            },
            {"role": "user", "content": "planting trees and pollution"},
            {
                "role": "agent",
                "content": (
                    "Great! Let's quickly go over the exercise first.\n\n"
                    "For the forest example:\n\n"
                    "Positive impact: Planting new trees.\n\n"
                    "Key Concept: Ecosystems\n\n"
                    "An ecosystem is a community of living organisms interacting with the non-living environment.\n\n"
                    "Your Turn:\n\n"
                    "Can you think of another ecosystem?"
                ),
            },
            {"role": "user", "content": "can you save the lecture notes to my google docs"},
        ]

        formatted = frontend_api._format_chat_messages_for_google_doc(messages)

        self.assertIn("ArkAI Lecture Notes: Environmental Science", formatted)
        self.assertIn("What is Environmental Science?", formatted)
        self.assertIn("Key Concept: Ecosystems", formatted)
        self.assertNotIn("Let's start", formatted)
        self.assertNotIn("Great!", formatted)
        self.assertNotIn("For the forest example", formatted)
        self.assertNotIn("Small Exercise", formatted)
        self.assertNotIn("Your Turn", formatted)

    def test_google_doc_formatter_excludes_previous_save_status_messages(self):
        messages = [
            {
                "role": "user",
                "content": (
                    "Teach me this roadmap session now: Environmental Science session 1. "
                    "Topic: Environmental Science. Give me a short explanation, one example, and one small exercise."
                ),
            },
            {
                "role": "agent",
                "content": (
                    "What is Environmental Science?\n\n"
                    "Environmental Science studies how humans and nature interact.\n\n"
                    "Example: The Water Cycle and Pollution\n\n"
                    "Pollution can move through water systems and affect living organisms."
                ),
            },
            {"role": "user", "content": "can you save the lecture notes to my google docs"},
            {
                "role": "agent",
                "content": (
                    "Note saved to Google Docs in folder 'Adaptive Learning Assistant Notes'\n\n"
                    "Document: https://docs.google.com/document/d/example/edit"
                ),
            },
            {"role": "user", "content": "the lecture more"},
            {
                "role": "agent",
                "content": (
                    "Absolutely! Let's dive a bit deeper into what we've discussed.\n\n"
                    "Types of Ecosystems\n\n"
                    "Ecosystems can be terrestrial or aquatic.\n\n"
                    "Quick Question:\n\n"
                    "If a bird goes extinct, what might happen?"
                ),
            },
            {
                "role": "agent",
                "content": (
                    "It looks like the save didn't go through. To save notes to Google Docs, "
                    "please connect your Google account from the ArkAI account menu first."
                ),
            },
            {"role": "user", "content": "save the lecture to google docs"},
        ]

        formatted = frontend_api._format_chat_messages_for_google_doc(messages)

        self.assertIn("ArkAI Lecture Notes: Environmental Science", formatted)
        self.assertIn("What is Environmental Science?", formatted)
        self.assertIn("Types of Ecosystems", formatted)
        self.assertNotIn("The Lecture More", formatted)
        self.assertNotIn("Note saved to Google Docs", formatted)
        self.assertNotIn("docs.google.com/document", formatted)
        self.assertNotIn("save didn't go through", formatted)
        self.assertNotIn("Quick Question", formatted)

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

    def test_teaching_request_requires_topic_and_level(self):
        self.assertTrue(frontend_api._is_teaching_request("teach me a lecture"))
        self.assertFalse(frontend_api._is_teaching_request("can you save this lecture to google docs"))
        self.assertTrue(frontend_api._is_google_save_request("can you save this lecture to google docs"))
        self.assertEqual(frontend_api._teaching_topic_from_message("teach me a lecture"), "")
        self.assertIn("What lecture topic", frontend_api._teaching_detail_question(""))
        self.assertEqual(frontend_api._teaching_topic_from_message("Teach me Python loops simply"), "Python loops")
        self.assertEqual(frontend_api._teaching_topic_from_message("teach me algebra as a beginner"), "algebra")
        self.assertEqual(frontend_api._teaching_level_from_message("teach me algebra as a beginner"), "beginner")

    def test_level_reply_resumes_pending_teaching_topic(self):
        messages = [
            {"role": "user", "content": "Teach me Python loops simply"},
            {
                "role": "assistant",
                "content": "What is your current level in Python loops: beginner, intermediate, or advanced?",
            },
            {"role": "user", "content": "beginner"},
        ]

        topic = frontend_api._pending_teaching_topic_from_messages(messages)
        resumed = frontend_api._resume_pending_teaching_message(topic, "beginner")

        self.assertEqual(topic, "Python loops")
        self.assertIn("Teach me Python loops", resumed)
        self.assertIn("as a beginner", resumed)
        self.assertIn("do not switch to another subject", resumed)

    def test_pending_teaching_topic_stops_after_real_agent_reply(self):
        messages = [
            {"role": "user", "content": "Teach me Python loops simply"},
            {
                "role": "assistant",
                "content": "What is your current level in Python loops simply: beginner, intermediate, or advanced?",
            },
            {"role": "user", "content": "beginner"},
            {"role": "assistant", "content": "What are Python loops?\n\nA loop repeats code."},
            {"role": "user", "content": "beginner"},
        ]

        self.assertEqual(frontend_api._pending_teaching_topic_from_messages(messages), "")

    def test_roadmap_calendar_uses_saved_start_when_message_says_this(self):
        roadmap = {
            "status": "success",
            "roadmap": {
                "topic": "Mathematics",
                "start_date": "2026-05-02",
                "preferred_calendar_time": "08:00",
                "phases": [
                    {
                        "title": "Foundation 1",
                        "goal": "Learn basics",
                        "sessions": [
                            {
                                "title": "Mathematics session 1",
                                "focus": "Mathematics",
                                "duration_minutes": 120,
                                "status": "planned",
                            }
                        ],
                    }
                ],
            },
        }

        with mock.patch.object(frontend_api, "get_roadmap", return_value=roadmap), \
             mock.patch(
                 "ark_learning_agent.productivity_mcp_server.google_oauth_status",
                 return_value={"connected": True},
             ), mock.patch(
                 "ark_learning_agent.productivity_mcp_server.create_calendar_event",
                 return_value={"status": "success", "message": "ok"},
             ) as create_event:
            result = __import__("asyncio").run(
                frontend_api._save_roadmap_sessions_to_google_calendar(
                    user_id="learner@example.com",
                    message="can you save this in my google calendar",
                    timezone_name="Asia/Bangkok",
                )
            )

        self.assertEqual(result["status"], "success")
        kwargs = create_event.call_args.kwargs
        self.assertEqual(kwargs["start_time_iso"], "2026-05-02T08:00:00+07:00")
        self.assertEqual(kwargs["end_time_iso"], "2026-05-02T10:00:00+07:00")

    def test_roadmap_calendar_recovers_start_from_recent_chat(self):
        roadmap = {
            "status": "success",
            "roadmap": {
                "topic": "Python Programming",
                "start_date": "",
                "preferred_calendar_time": "",
                "phases": [
                    {
                        "title": "Foundation 1",
                        "goal": "Learn basics",
                        "sessions": [
                            {
                                "title": "Python Programming session 1",
                                "focus": "Python Programming",
                                "duration_minutes": 60,
                                "status": "planned",
                            }
                        ],
                    }
                ],
            },
        }
        client_messages = [
            {
                "role": "user",
                "content": "yes let's start at 4am tomorrow for 2 weeks",
            },
            {"role": "user", "content": "I already gave you the time"},
        ]

        with mock.patch.object(frontend_api, "get_roadmap", return_value=roadmap), \
             mock.patch(
                 "ark_learning_agent.productivity_mcp_server.google_oauth_status",
                 return_value={"connected": True},
             ), mock.patch(
                 "ark_learning_agent.productivity_mcp_server.create_calendar_event",
                 return_value={"status": "success", "message": "ok"},
             ) as create_event:
            result = __import__("asyncio").run(
                frontend_api._save_roadmap_sessions_to_google_calendar(
                    user_id="learner@example.com",
                    message="I already gave you the time",
                    timezone_name="Asia/Bangkok",
                    client_messages=client_messages,
                )
            )

        self.assertEqual(result["status"], "success")
        kwargs = create_event.call_args.kwargs
        self.assertEqual(kwargs["start_time_iso"], "2026-05-02T04:00:00+07:00")
        self.assertEqual(kwargs["end_time_iso"], "2026-05-02T05:00:00+07:00")

    def test_google_tasks_are_created_from_roadmap_not_lecture(self):
        roadmap = {
            "status": "success",
            "roadmap": {
                "topic": "Mathematics",
                "start_date": "2026-05-02",
                "phases": [],
            },
        }
        with mock.patch.object(frontend_api, "get_roadmap", return_value=roadmap), \
             mock.patch(
                 "ark_learning_agent.productivity_mcp_server.google_oauth_status",
                 return_value={"connected": True},
             ), mock.patch(
                 "ark_learning_agent.productivity_mcp_server.create_roadmap_tasks",
                 return_value={"status": "success", "message": "Created 1 roadmap task(s) in Google Tasks."},
             ) as create_tasks:
            result = __import__("asyncio").run(
                frontend_api._save_tutor_chat_to_google_task("learner@example.com", "session-1", client_messages=[])
            )

        self.assertEqual(result["status"], "success")
        create_tasks.assert_called_once_with(user_id="learner@example.com", include_due_dates=True)

    def test_complete_tutor_roadmap_request_saves_plan_roadmap(self):
        saved_args = {}

        def fake_build(**kwargs):
            saved_args.update(kwargs)
            return {
                "status": "success",
                "roadmap": {
                    "topic": kwargs["topic"],
                    "available_time": kwargs["available_time"],
                    "deadline_days": kwargs["deadline_days"],
                    "preferred_calendar_time": kwargs["preferred_calendar_time"],
                    "phases": [
                        {
                            "sessions": [
                                {"title": "Python Loops session 1"},
                                {"title": "Python Loops session 2"},
                            ]
                        }
                    ],
                },
                "summary": {"total_sessions": 2},
            }

        with mock.patch.object(learner_state, "get_roadmap", return_value={"status": "not_found"}), \
             mock.patch.object(frontend_api, "get_roadmap", return_value={"status": "not_found"}), \
             mock.patch.object(frontend_api, "build_or_update_roadmap", side_effect=fake_build):
            result = __import__("asyncio").run(
                frontend_api._handle_tutor_roadmap_request(
                    user_id="learner@example.com",
                    message="can you create me a 7 day roadmap to learn python loops starting tomorrow at 9am for 1 hour?",
                    timezone_name="Asia/Bangkok",
                )
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(saved_args["topic"], "python loops")
        self.assertEqual(saved_args["deadline_days"], 7)
        self.assertEqual(saved_args["available_time"], 60)
        self.assertTrue(saved_args["force_rebuild"])
        self.assertIn("Saved your 7-day python loops roadmap to Plan.", result["message"])

    def test_partial_tutor_roadmap_request_asks_for_missing_schedule_details(self):
        with mock.patch.object(frontend_api, "get_roadmap", return_value={"status": "not_found"}), \
             mock.patch.object(frontend_api, "build_or_update_roadmap") as build_roadmap:
            result = __import__("asyncio").run(
                frontend_api._handle_tutor_roadmap_request(
                    user_id="learner@example.com",
                    message="can you create me a 7 day roadmap to learn python loops?",
                    timezone_name="Asia/Bangkok",
                )
            )

        self.assertEqual(result["status"], "needs_details")
        self.assertIn("Got it: python loops.", result["message"])
        self.assertIn("What date would you like to start", result["message"])
        build_roadmap.assert_not_called()

    def test_vague_tutor_roadmap_request_asks_for_details(self):
        with mock.patch.object(frontend_api, "get_roadmap", return_value={"status": "not_found"}), \
             mock.patch.object(frontend_api, "build_or_update_roadmap") as build_roadmap:
            result = __import__("asyncio").run(
                frontend_api._handle_tutor_roadmap_request(
                    user_id="guest:abc123",
                    message="create a roadmap for me",
                    timezone_name="Asia/Bangkok",
                )
            )

        self.assertEqual(result["status"], "needs_topic")
        self.assertIn("What topic should the roadmap cover", result["message"])
        self.assertIn("what date would you like to start", result["message"])
        self.assertIn("how long do you want to study", result["message"])
        build_roadmap.assert_not_called()

    def test_vague_tutor_roadmap_request_does_not_reuse_existing_polluted_topic(self):
        existing = {
            "status": "success",
            "roadmap": {
                "topic": "me for the topic: algebra",
                "deadline_days": 7,
                "available_time": 45,
                "phases": [],
            },
        }

        with mock.patch.object(frontend_api, "get_roadmap", return_value=existing), \
             mock.patch.object(frontend_api, "build_or_update_roadmap") as build_roadmap:
            result = __import__("asyncio").run(
                frontend_api._handle_tutor_roadmap_request(
                    user_id="learner@example.com",
                    message="create a roadmap for me",
                    timezone_name="Asia/Bangkok",
                )
            )

        self.assertEqual(result["status"], "needs_topic")
        self.assertIn("What topic should the roadmap cover", result["message"])
        build_roadmap.assert_not_called()

    def test_vague_tutor_roadmap_request_does_not_treat_weeks_as_topic(self):
        with mock.patch.object(frontend_api, "get_roadmap", return_value={"status": "not_found"}), \
             mock.patch.object(frontend_api, "build_or_update_roadmap") as build_roadmap:
            result = __import__("asyncio").run(
                frontend_api._handle_tutor_roadmap_request(
                    user_id="guest:abc123",
                    message="create me one roadmap for 2 weeks",
                    timezone_name="Asia/Bangkok",
                )
            )

        self.assertEqual(result["status"], "needs_topic")
        self.assertIn("What topic should the roadmap cover", result["message"])
        build_roadmap.assert_not_called()

    def test_topic_only_tutor_roadmap_request_asks_for_schedule_details(self):
        with mock.patch.object(frontend_api, "get_roadmap", return_value={"status": "not_found"}), \
             mock.patch.object(frontend_api, "build_or_update_roadmap") as build_roadmap:
            result = __import__("asyncio").run(
                frontend_api._handle_tutor_roadmap_request(
                    user_id="learner@example.com",
                    message="create a roadmap for me for the topic: algebra",
                    timezone_name="Asia/Bangkok",
                )
            )

        self.assertEqual(result["status"], "needs_details")
        self.assertIn("Got it: algebra.", result["message"])
        self.assertIn("What date would you like to start", result["message"])
        self.assertIn("how many days should the roadmap cover", result["message"])
        self.assertIn("what time do you prefer", result["message"])
        self.assertIn("how long do you want to study each session", result["message"])
        build_roadmap.assert_not_called()

    def test_pending_roadmap_detail_reply_builds_original_topic(self):
        messages = [
            {"role": "user", "content": "can you help me create a roadmap to learn programming?"},
            {
                "role": "assistant",
                "content": "Got it: programming. What date would you like to start, how many days should the roadmap cover, what time do you prefer, and how long do you want to study each session?",
            },
            {
                "role": "user",
                "content": "I wanna start tomorrow, for 2 weeks. and I prefer learning in the morning at 4am and 1 hr each session",
            },
        ]

        topic = frontend_api._pending_roadmap_topic_from_messages(messages)
        resumed = frontend_api._resume_pending_roadmap_message(topic, messages[-1]["content"])

        self.assertEqual(topic, "programming")
        self.assertIn("learn programming", resumed)
        self.assertTrue(frontend_api._has_roadmap_schedule_details(resumed))
        self.assertEqual(frontend_api._parse_roadmap_deadline_days(resumed), 14)
        self.assertEqual(frontend_api._parse_calendar_clock_from_message(resumed), "04:00")
        start = frontend_api._calendar_start_from_message(resumed, "Asia/Bangkok")
        self.assertIsNotNone(start)
        self.assertEqual(start.hour, 4)

    def test_generic_roadmap_detail_reply_extracts_topic_and_time_range(self):
        messages = [
            {
                "role": "assistant",
                "content": "Sure. What topic should the roadmap cover, what date would you like to start, how many days should the roadmap cover, what time do you prefer, and how long do you want to study each session?",
            },
            {
                "role": "user",
                "content": "programming I wanna start tomorrow. 5 days. I prefer study at 5am till 6am",
            },
        ]
        user_message = messages[-1]["content"]

        self.assertTrue(frontend_api._has_pending_roadmap_detail_question(messages))
        self.assertEqual(frontend_api._parse_roadmap_topic_from_message(user_message), "programming")
        self.assertEqual(frontend_api._parse_roadmap_deadline_days(user_message), 5)
        self.assertEqual(frontend_api._parse_study_minutes(user_message), 60)
        self.assertEqual(frontend_api._parse_calendar_clock_from_message(user_message), "05:00")
        self.assertTrue(frontend_api._has_roadmap_schedule_details(user_message))

    def test_typo_learn_french_and_multi_message_month_details(self):
        messages = [
            {"role": "user", "content": "create me a roadmap for leaning French"},
            {
                "role": "assistant",
                "content": "Sure. What topic should the roadmap cover, what date would you like to start, how many days should the roadmap cover, what time do you prefer, and how long do you want to study each session?",
            },
            {
                "role": "user",
                "content": "a month I wann do it this whold month May . study every morning at 7am until 9am.",
            },
            {"role": "assistant", "content": "Got it: French. What date would you like to start, how many days should the roadmap cover, what time do you prefer, and how long do you want to study each session?"},
            {"role": "user", "content": "tomorrow. 30days"},
        ]

        topic = frontend_api._pending_roadmap_topic_from_messages(messages)
        details = frontend_api._pending_roadmap_detail_text(messages, messages[-1]["content"])
        resumed = frontend_api._resume_pending_roadmap_message(topic, details)

        self.assertEqual(frontend_api._parse_roadmap_topic_from_message(messages[0]["content"]), "French")
        self.assertEqual(
            frontend_api._parse_roadmap_topic_from_message("Create a roadmap to learn French. a month this whole month May. study every morning"),
            "French",
        )
        self.assertEqual(topic, "French")
        self.assertIn("7am until 9am", details)
        self.assertIn("tomorrow. 30days", details)
        self.assertEqual(frontend_api._parse_roadmap_deadline_days(resumed), 30)
        self.assertEqual(frontend_api._parse_study_minutes(resumed), 120)
        self.assertEqual(frontend_api._parse_calendar_clock_from_message(resumed), "07:00")
        self.assertTrue(frontend_api._has_roadmap_schedule_details(resumed))

    def test_get_roadmap_cleans_schedule_text_from_topic_and_sessions(self):
        polluted_topic = "French. a month I wann do it this whold month May . study every morning. a month I wann do it this whold month May . study every morning"
        polluted = {
            "roadmap_id": "roadmap-1",
            "topic": polluted_topic,
            "goal": f"Learn {polluted_topic}",
            "phases": [
                {
                    "phase_id": "phase-1",
                    "title": "Foundation 1",
                    "goal": f"Move {polluted_topic} from beginner understanding toward stronger applied mastery.",
                    "focus_topics": [polluted_topic],
                    "expected_outcome": f"Learner can explain and apply {polluted_topic} in a short exercise.",
                    "sessions": [
                        {
                            "session_id": "phase-1-session-1",
                            "title": f"{polluted_topic.title()} session 1",
                            "focus": polluted_topic,
                            "duration_minutes": 120,
                            "status": "planned",
                            "due_date": "2026-05-02",
                        }
                    ],
                }
            ],
        }

        with mock.patch.object(learner_state, "_load_roadmap", return_value=polluted):
            result = learner_state.get_roadmap("learner@example.com")

        roadmap = result["roadmap"]
        session = roadmap["phases"][0]["sessions"][0]
        self.assertEqual(roadmap["topic"], "French")
        self.assertEqual(session["focus"], "French")
        self.assertEqual(session["title"], "French session 1")
        self.assertNotIn("whold month", str(roadmap))

    def test_five_day_standard_roadmap_ignores_unrelated_weak_topics(self):
        with mock.patch.object(learner_state, "_load_roadmap", return_value=None), \
             mock.patch.object(learner_state, "_save_roadmap"), \
             mock.patch.object(learner_state, "get_learner_profile", return_value={"status": "success"}), \
             mock.patch.object(learner_state, "save_learner_profile"), \
             mock.patch.object(
                 learner_state,
                 "get_mastery_snapshot",
                 return_value={
                     "topics": [
                         {"topic": "English-vocabs.txt", "score": 0.1},
                         {"topic": "Can you summarize that", "score": 0.2},
                     ]
                 },
             ):
            result = learner_state.build_or_update_roadmap(
                user_id="learner@example.com",
                topic="programming",
                goal="Learn programming",
                level="beginner",
                available_time=60,
                deadline_days=5,
                start_date="2026-05-02",
                preferred_calendar_time="05:00",
                force_rebuild=True,
            )

        sessions = [
            session
            for phase in result["roadmap"]["phases"]
            for session in phase.get("sessions", [])
        ]
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["roadmap"]["deadline_days"], 5)
        self.assertEqual(len(sessions), 5)
        self.assertTrue(all(session["focus"] == "programming" for session in sessions))
        self.assertNotIn("English-vocabs.txt", str(result["roadmap"]))
        self.assertNotIn("Can you summarize that", str(result["roadmap"]))

    def test_two_week_standard_roadmap_creates_daily_sessions(self):
        with mock.patch.object(learner_state, "_load_roadmap", return_value=None), \
             mock.patch.object(learner_state, "_save_roadmap"), \
             mock.patch.object(learner_state, "get_learner_profile", return_value={"status": "success"}), \
             mock.patch.object(learner_state, "save_learner_profile"), \
             mock.patch.object(learner_state, "get_mastery_snapshot", return_value={"topics": []}):
            result = learner_state.build_or_update_roadmap(
                user_id="learner@example.com",
                topic="Python Programming",
                goal="Learn Python Programming",
                level="beginner",
                available_time=60,
                deadline_days=14,
                start_date="2026-05-02",
                preferred_calendar_time="04:00",
                force_rebuild=True,
            )

        sessions = [
            session
            for phase in result["roadmap"]["phases"]
            for session in phase.get("sessions", [])
        ]
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(sessions), 14)
        self.assertEqual(sessions[0]["due_date"], "2026-05-02")
        self.assertEqual(sessions[-1]["due_date"], "2026-05-15")
        self.assertTrue(all(session["duration_minutes"] == 60 for session in sessions))

    def test_tutor_roadmap_update_records_duration_and_asks_for_start_date(self):
        existing = {
            "status": "success",
            "roadmap": {
                "topic": "python loops",
                "deadline_days": 7,
                "available_time": 45,
                "level": "beginner",
                "phases": [],
            },
        }
        saved_args = {}

        def fake_build(**kwargs):
            saved_args.update(kwargs)
            return {
                "status": "success",
                "roadmap": {
                    "topic": kwargs["topic"],
                    "available_time": kwargs["available_time"],
                    "deadline_days": kwargs["deadline_days"],
                    "preferred_calendar_time": kwargs["preferred_calendar_time"],
                    "phases": [{"sessions": [{"title": "Python Loops session 1"}]}],
                },
                "summary": {"total_sessions": 1},
            }

        with mock.patch.object(frontend_api, "get_roadmap", return_value=existing), \
             mock.patch.object(frontend_api, "build_or_update_roadmap", side_effect=fake_build):
            result = __import__("asyncio").run(
                frontend_api._handle_tutor_roadmap_request(
                    user_id="learner@example.com",
                    message="I wanna study 1 hr aday at 9 am in the morning please save to the roadmap",
                    timezone_name="Asia/Bangkok",
                )
            )

        self.assertEqual(saved_args["topic"], "python loops")
        self.assertEqual(saved_args["available_time"], 60)
        self.assertEqual(saved_args["preferred_calendar_time"], "09:00")
        self.assertEqual(saved_args["start_date"], "")
        self.assertIn("What date should the first session start", result["message"])

    def test_google_connected_acknowledgement_checks_server_and_asks_start_date(self):
        roadmap = {
            "status": "success",
            "roadmap": {
                "topic": "python loops",
                "preferred_calendar_time": "09:00",
                "start_date": "",
            },
        }

        with mock.patch.object(
            productivity_mcp_server,
            "google_oauth_status",
            return_value={"status": "success", "connected": True},
        ), mock.patch.object(frontend_api, "get_roadmap", return_value=roadmap):
            result = __import__("asyncio").run(
                frontend_api._handle_google_connected_acknowledgement("learner@example.com")
            )

        self.assertEqual(result["status"], "needs_time")
        self.assertIn("Google saves is connected now", result["message"])
        self.assertIn("What date should the first session start", result["message"])

    def test_roadmap_calendar_request_asks_schedule_before_auth(self):
        roadmap = {
            "status": "success",
            "roadmap": {
                "topic": "python loops",
                "preferred_calendar_time": "",
                "start_date": "",
                "phases": [],
            },
        }
        with mock.patch(
            "ark_learning_agent.productivity_mcp_server.google_oauth_status",
            return_value={"connected": False},
        ) as oauth_status, mock.patch.object(frontend_api, "get_roadmap", return_value=roadmap):
            result = __import__("asyncio").run(
                frontend_api._save_roadmap_sessions_to_google_calendar(
                    user_id="learner@example.com",
                    message="add my roadmap sessions to google calendar",
                    timezone_name="Asia/Bangkok",
                )
            )

        self.assertEqual(result["status"], "needs_time")
        self.assertIn("What date should the first roadmap session start", result["message"])
        oauth_status.assert_not_called()

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

    def test_standard_roadmap_ignores_unrelated_material_filename_mastery(self):
        with mock.patch.object(learner_state, "_load_roadmap", return_value=None), \
             mock.patch.object(learner_state, "_save_roadmap"), \
             mock.patch.object(learner_state, "get_learner_profile", return_value={"status": "success"}), \
             mock.patch.object(learner_state, "save_learner_profile"), \
             mock.patch.object(
                 learner_state,
                 "get_mastery_snapshot",
                 return_value={"topics": [{"topic": "English-vocabs.txt", "score": 0.2}]},
             ):
            result = learner_state.build_or_update_roadmap(
                user_id="learner@example.com",
                topic="Trigo3",
                goal="Practice trigonometry",
                level="advanced",
                available_time=45,
                deadline_days=7,
                start_date="2026-07-01",
                force_rebuild=True,
            )

        self.assertEqual(result["status"], "success")
        first_session = result["roadmap"]["phases"][0]["sessions"][0]
        self.assertEqual(first_session["focus"], "Trigo3")
        self.assertEqual(first_session["title"], "Trigo3 session 1")
        self.assertNotIn("English-vocabs.txt", str(result["roadmap"]))

    def test_get_roadmap_cleans_uploaded_filename_session_focus(self):
        polluted = {
            "roadmap_id": "roadmap-1",
            "topic": "Trigo3",
            "phases": [
                {
                    "phase_id": "phase-1",
                    "title": "Foundation 1",
                    "focus_topics": ["English-vocabs.txt"],
                    "expected_outcome": "Learner can explain and apply English-vocabs.txt.",
                    "sessions": [
                        {
                            "session_id": "phase-1-session-1",
                            "title": "English-Vocabs.Txt session 1",
                            "focus": "English-vocabs.txt",
                            "duration_minutes": 45,
                            "status": "planned",
                        }
                    ],
                }
            ],
        }

        with mock.patch.object(learner_state, "_load_roadmap", return_value=polluted):
            result = learner_state.get_roadmap("learner@example.com")

        session = result["roadmap"]["phases"][0]["sessions"][0]
        self.assertEqual(session["focus"], "Trigo3")
        self.assertEqual(session["title"], "Trigo3 session 1")
        self.assertEqual(result["summary"]["total_sessions"], 1)

    def test_custom_material_assessment_does_not_overwrite_profile_topic(self):
        questions = [
            {
                "question_type": "multiple_choice",
                "prompt": "Pick one.",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "explanation": "Because A.",
                "concept": "vocab",
            }
        ]

        with mock.patch.object(learner_state, "save_learner_profile") as save_profile, \
             mock.patch.object(learner_state, "get_firestore_client", return_value=None), \
             mock.patch.object(learner_state, "init_sqlite_fallback"), \
             mock.patch.object(learner_state, "_connect_sqlite") as connect_sqlite:
            conn = mock.Mock()
            connect_sqlite.return_value = conn
            result = learner_state.create_custom_assessment(
                user_id="learner@example.com",
                topic="English-vocabs.txt",
                questions=questions,
                assessment_type="mock_test",
            )

        self.assertEqual(result["status"], "success")
        save_profile.assert_not_called()

    def test_material_mock_structure_parses_requested_question_types(self):
        question_count, distribution, instruction = materials._parse_requested_question_structure(
            "Generate 20 MCQ",
            default_count=5,
        )

        self.assertEqual(question_count, 20)
        self.assertEqual(distribution, {"multiple_choice": 20})
        self.assertIn("20 multiple choice", instruction)

    def test_material_mock_structure_sums_mixed_request(self):
        question_count, distribution, instruction = materials._parse_requested_question_structure(
            "2 short answers, 1 essay, 3 multiple choice",
            default_count=5,
        )

        self.assertEqual(question_count, 6)
        self.assertEqual(
            distribution,
            {"short_answer": 2, "essay": 1, "multiple_choice": 3},
        )
        self.assertIn("3 multiple choice", instruction)

    def test_pdf_extraction_uses_gemini_when_parser_finds_no_text(self):
        class FakeModels:
            def generate_content(self, **kwargs):
                self.kwargs = kwargs
                return mock.Mock(text="Question 1. What is overfitting? A. Memorizing training noise")

        fake_client = mock.Mock()
        fake_client.models = FakeModels()

        with mock.patch.object(materials, "_get_genai_client", return_value=fake_client):
            text = materials._extract_text_from_pdf(b"%PDF-1.4\nstream\nnot-text\nendstream")

        self.assertIn("Question 1", text)

    def test_evaluation_snapshot_combines_materials_assessments_and_roadmap(self):
        state = {
            "status": "success",
            "current_topic": "Machine Learning",
            "recent_topics": ["Machine Learning"],
            "weak_topics": ["overfitting"],
            "latest_activity": {"topic": "Machine Learning", "activity_type": "mock_test"},
            "mastery": {"overall_score": 0.62, "topics": []},
            "roadmap": {"topic": "Machine Learning"},
            "roadmap_summary": {
                "phase_count": 2,
                "total_sessions": 6,
                "completed_sessions": 2,
                "missed_sessions": 1,
                "completion_rate": 0.333,
                "next_session": {"title": "Regularization practice"},
            },
        }
        history = [
            {"topic": "Machine Learning", "activity_type": "mock_test", "score": 0.7},
            {"topic": "Machine Learning", "activity_type": "roadmap_session", "score": None},
        ]
        assessments = [
            {"assessment_type": "mock_test", "status": "submitted", "score": 0.7},
            {"assessment_type": "diagnostic", "status": "open", "score": None},
        ]
        materials_payload = {
            "materials": [
                {"name": "ml-notes.pdf"},
                {"name": "sample-exam.pdf"},
            ]
        }

        with mock.patch.object(learner_state, "get_learner_state", return_value=state), \
             mock.patch.object(learner_state, "get_learning_history", return_value={"history": history}), \
             mock.patch.object(learner_state, "_list_assessment_records", return_value=assessments), \
             mock.patch("ark_learning_agent.materials.list_learning_materials", return_value=materials_payload):
            snapshot = learner_state.get_evaluation_snapshot("learner@example.com")

        self.assertEqual(snapshot["status"], "success")
        self.assertEqual(snapshot["coverage"]["material_count"], 2)
        self.assertEqual(snapshot["coverage"]["mock_test_count"], 1)
        self.assertEqual(snapshot["quality"]["completed_sessions"], 2)
        self.assertIn("overfitting", " ".join(snapshot["risks"]))
        self.assertIn("Regularization practice", " ".join(snapshot["recommended_actions"]))

    def test_learner_state_filters_file_and_prompt_weak_topics(self):
        mastery = {
            "status": "success",
            "overall_score": 0.4,
            "topics": [
                {"topic": "CH01.pdf", "score": 0.1},
                {"topic": "English-vocabs.txt", "score": 0.2},
                {"topic": "can you summarize that", "score": 0.2},
                {"topic": "overfitting", "score": 0.3},
            ],
        }

        with mock.patch.object(learner_state, "get_learner_profile", return_value={"status": "not_found"}), \
             mock.patch.object(learner_state, "get_learning_history", return_value={"history": []}), \
             mock.patch.object(learner_state, "list_study_notes", return_value={"notes": []}), \
             mock.patch.object(learner_state, "get_mastery_snapshot", return_value=mastery), \
             mock.patch.object(learner_state, "get_roadmap", return_value={"status": "not_found"}):
            state = learner_state.get_learner_state("learner@example.com")

        self.assertEqual(state["weak_topics"], ["overfitting"])

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
