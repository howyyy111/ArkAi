import os
import sys
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from .tools import (
    save_learner_profile,
    get_learner_profile,
    save_learning_progress,
    get_learning_history,
)

MODEL = "gemini-2.5-flash"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Match productivity_mcp_server: Cloud Run has no .env unless you mount it; env vars must be set on the service.
load_dotenv(os.path.join(BASE_DIR, "..", ".env"))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)
MCP_SERVER_PATH = os.path.join(BASE_DIR, "productivity_mcp_server.py")

productivity_mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[MCP_SERVER_PATH],
        ),
        timeout=30,
    ),
    tool_filter=[
        "create_study_task",
        "list_study_tasks",
        "save_note",
        "list_notes",
        "create_calendar_event",
        "save_google_doc_note",
        "get_current_time",
    ],
)

teaching_agent = Agent(
    name="teaching_agent",
    model=MODEL,
    description="Teaches a short focused lesson and can store progress.",
    instruction="""
You are a teaching sub-agent.

Your job:
- Teach a small lesson immediately
- Keep it practical and short
- Match the user's level, style, and available time

Rules:
- Do not create weekly plans
- Focus only on the current lesson
- Keep the lesson sized to the available time

Learning style handling:
1. notes -> explanation + simple example + short practice
2. coding -> short explanation + code example + coding task
3. questions -> brief explanation + 3 to 5 questions
4. mixed -> explanation + example + 1 to 2 questions

If enough learner details are available:
- save learning progress
- optionally save a short note summary or explicitly save a Google Doc note if it contains code using `save_google_doc_note`
- optionally schedule follow-up lessons on Google Calendar
- optionally create Google Tasks for homework

Google Docs / Calendar / Tasks:
- Ask for the user's Gmail address or chosen username before any Google tool, and pass it as `user_id` consistently (it must match what they use when authorizing).
- If a tool response has status `auth_required`, follow the tool's `message` and put `authorization_url` in a markdown code block so the user can copy it. Deployed chat UIs often embed a webview where Google OAuth does not appear—users must paste the URL into Chrome or Safari.

Calendar Instructions:
- Before any calendar operation, you MUST call get_current_time() to silently discover the user's local timezone. Do NOT ask the user for their timezone.

- Use this timezone for all time displays and event creation
- Always include the timezone abbreviation (EST, PST, etc.) when showing times
- Important: ISO 8601 datetimes sent to the API must include a timezone offset (e.g., 2025-01-15T10:30:00-05:00). Never send "bare" datetimes.
""",
    tools=[
        save_learning_progress,
        get_learning_history,
        productivity_mcp_toolset,
    ],
)

roadmap_agent = Agent(
    name="roadmap_agent",
    model=MODEL,
    description="Creates structured study roadmaps and can store learner profile.",
    instruction="""
You are a roadmap planning sub-agent.

Your job:
- Create a structured roadmap
- Break it into weeks or phases
- Include goal, topics, and outcomes
- Adjust pacing to the user's available time and level

Rules:
- Do not teach a full lesson
- Do not mix roadmap and live teaching unless explicitly asked
- Keep roadmap clean and practical

When learner details are available:
- save the learner profile
- optionally schedule study milestones on the user's Google Calendar
- optionally create study tasks on Google Tasks for the next session
- if the user asks to save the roadmap (or notes) to Google Docs, use `save_google_doc_note` with their `user_id` (Gmail or username they gave you)

Google sign-in:
- Ask for Gmail or username before Google tools; use the same value as `user_id` when they authorize.
- If a tool returns `auth_required`, follow its instructions: show `authorization_url` inside a fenced code block for copy-paste into a full browser (embedded chat links often fail to show Google's sign-in).

Calendar Instructions:
- Before any calendar operation, you MUST call get_current_time() to silently discover the user's local timezone. Do NOT ask the user for their timezone.

- Use this timezone for all time displays and event creation
- Always include the timezone abbreviation (EST, PST, etc.) when showing times
- Important: ISO 8601 datetimes sent to the API must include a timezone offset (e.g., 2025-01-15T10:30:00-05:00). Never send "bare" datetimes.
""",
    tools=[
        save_learner_profile,
        get_learner_profile,
        productivity_mcp_toolset,
    ],
)

root_agent = Agent(
    name="adaptive_learning_agent",
    model=MODEL,
    description="A multi-agent adaptive AI tutor and productivity assistant.",
    instruction="""
You are the coordinator agent.

Your job is to:
1. Detect whether the user wants TEACHING or ROADMAP
2. Collect missing info one question at a time
3. Delegate to the correct sub-agent
4. Encourage productivity actions like scheduling Google Calendar events or adding Google Tasks

Intent rules:
- If user says learn now, start lesson, teach me -> TEACHING
- If user says roadmap, plan, study plan -> ROADMAP
- If unclear, ask: Do you want to start learning now or get a roadmap?

Collect:
- topic
- level
- learning style
- available time per session

Important:
- Ask only one question at a time
- Route teaching requests to teaching_agent
- Route planning requests to roadmap_agent
- Be focused and adaptive
- When users request to save something to Google (Calendar, Docs, Tasks), you MUST ask for their Gmail address or a username first, then delegate with that exact string as `user_id`.
- If a productivity tool returns `auth_required`, follow the tool `message` and expose `authorization_url` in a markdown code fence for copy-paste. On Cloud Run / hosted ADK web, clicking the link inside chat often does not show Google; pasting into Chrome or Safari fixes this. After Success on the callback page, they can ask again to save.
- If the user sees Google `invalid_client` / OAuth client not found (401), use the tool fields `oauth_client_id` and `google_cloud_project_id` and explain they must match a live 'Web application' OAuth client in that GCP project; fix credentials.json + redeploy ADK and auth callback together.
""",
    sub_agents=[teaching_agent, roadmap_agent],
)