import re

with open("ark_learning_agent/frontend_api.py", "r") as f:
    content = f.read()

# 1. async def _resolve_request_context
content = re.sub(
    r"def _resolve_request_context\(",
    r"async def _resolve_request_context(",
    content
)

# 2. await _resolve_request_context
content = re.sub(
    r"context = _resolve_request_context\(",
    r"context = await _resolve_request_context(",
    content
)

# 3. Inside _resolve_request_context: asyncio.to_thread
content = content.replace(
    "authenticated_user_id, _ = _resolve_authenticated_user(payload, request)",
    "authenticated_user_id, _ = await asyncio.to_thread(_resolve_authenticated_user, payload, request)"
)
content = re.sub(
    r"identity = get_or_create_browser_identity\(\s*client_id=client_id,\s*authenticated_user_id=authenticated_user_id,\s*reset_identity=reset_identity,\s*\)",
    r"identity = await asyncio.to_thread(\n        get_or_create_browser_identity,\n        client_id=client_id,\n        authenticated_user_id=authenticated_user_id,\n        reset_identity=reset_identity,\n    )",
    content
)
content = re.sub(
    r"session = get_or_create_chat_session\(\s*client_id=str\(identity\[\"client_id\"\]\),\s*user_id=str\(identity\[\"user_id\"\]\),\s*session_id=session_id,\s*reset_session=reset_session,\s*\)",
    r"session = await asyncio.to_thread(\n        get_or_create_chat_session,\n        client_id=str(identity[\"client_id\"]),\n        user_id=str(identity[\"user_id\"]),\n        session_id=session_id,\n        reset_session=reset_session,\n    )",
    content
)

# 4. In api_auth_session
content = content.replace(
    "user_id = _verify_firebase_id_token_email(id_token)",
    "user_id = await asyncio.to_thread(_verify_firebase_id_token_email, id_token)"
)
content = content.replace(
    "session_cookie = _create_firebase_session_cookie(id_token)",
    "session_cookie = await asyncio.to_thread(_create_firebase_session_cookie, id_token)"
)

# 5. Functions to wrap in await asyncio.to_thread(func, ...)
funcs = [
    "get_demo_kit",
    "get_learner_state",
    "get_mastery_snapshot",
    "get_roadmap",
    "list_learning_materials",
    "list_chat_sessions",
    "get_chat_messages",
    "get_intervention_plan",
    "get_evaluation_snapshot",
    "google_oauth_status",
    "get_google_authorization_url",
    "delete_chat_session",
    "delete_all_chat_sessions",
    "create_assessment",
    "submit_assessment",
    "build_or_update_roadmap",
    "delete_roadmap",
    "update_roadmap_session",
    "create_roadmap_tasks",
    "create_calendar_event",
    "save_learning_material",
    "tutor_from_materials",
    "create_mock_test_from_materials",
    "delete_learning_material",
    "delete_all_learning_materials",
    "delete_learning_history_item",
    "delete_all_learning_history",
    "generate_weekly_report",
    "save_weekly_report_doc",
    "save_assessment_doc",
    "append_chat_message",
    "_save_tutor_chat_to_google_drive",
    "_save_tutor_chat_to_google_task",
    "_save_roadmap_sessions_to_google_calendar",
    "_save_tutor_chat_to_google_calendar",
    "_save_tutor_chat_to_google_doc",
    "save_learning_progress"
]

for func in funcs:
    # Match func(...) or func(
    # Because some calls are multi-line, we'll do a regex to replace `func(` with `await asyncio.to_thread(func, `
    # We must ensure we don't replace def func( or import func
    content = re.sub(
        rf"(?<!def )(?<!async def )(?<!import )(?<!from )(\b{func}\()",
        rf"await asyncio.to_thread({func}, ",
        content
    )

with open("ark_learning_agent/frontend_api.py", "w") as f:
    f.write(content)
print("Done")
