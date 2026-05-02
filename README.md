# ARKAIS

ARKAIS is an adaptive AI learning assistant that helps a learner move from "I need to understand this" to "I have a plan, practice, evidence of progress, and saved study work."

The application combines a browser-based learning dashboard, a FastAPI backend, Google ADK multi-agent tutoring, a materials library, learner progress persistence, diagnostics, roadmap planning, and Google Workspace actions through MCP tools.

For hackathon judges and testers, start here:

**[Hackathon Tester Guide](./HACKATHON_TESTER_GUIDE.md)**

That guide explains how to run the app and how to use the included demo files:

- [`mock_ml_notes.md`](./mock_ml_notes.md)
- [`mock_ml_exam.md`](./mock_ml_exam.md)

## What ARKAIS Does

ARKAIS is designed for students who need a personal tutor that can:

- explain a topic in a focused way
- generate quizzes and diagnostics
- build a study roadmap
- track progress and mastery
- use uploaded notes as study material
- create mock tests from those notes
- generate progress insights and weekly reports
- save learning outputs into Google Docs, Google Tasks, Google Calendar, or Google Drive

The goal is not only to answer questions, but to support a full learning workflow.

## Core Features

### Adaptive Tutor

The Tutor view lets a learner ask a focused question, continue a study session, attach temporary files, use voice input, and receive explanations, examples, practice tasks, or quizzes.

The tutor is backed by a Google ADK multi-agent setup. The root coordinator routes requests to specialized agents such as:

- Teaching Agent
- Roadmap Agent
- Evaluator Agent
- Intervention Agent
- Report Agent

### Study Roadmaps

The Plan view helps a learner create a structured roadmap from:

- topic
- learning goal
- current level
- study time
- deadline
- start date
- optional Google Calendar sync

Roadmaps are broken into phases and sessions. Sessions can be marked as complete or pending, and ARKAIS can recommend recovery behavior when the learner falls behind.

### Diagnostics And Mastery

ARKAIS can generate short diagnostic assessments, score answers, and update learner mastery. This gives the product a measurable learning loop:

1. Ask or study a topic.
2. Take a diagnostic.
3. Receive a score and feedback.
4. Update mastery signals.
5. Generate better next steps.

### Materials Library

The Materials view lets a learner upload notes, files, pasted text, and supported study assets. ARKAIS extracts usable text where possible and stores material metadata.

Current supported local upload types include:

- `.txt`
- `.md`
- `.csv`
- `.json`
- `.html`
- `.css`
- `.js`
- `.py`
- `.png`
- `.jpg`
- `.jpeg`
- `.webp`
- `.pdf` in selected mock-test flows

The included demo material files are intended for judge testing:

- `mock_ml_notes.md`: short machine learning notes
- `mock_ml_exam.md`: sample exam style and structure

### Mock Test Generation

The Materials view includes a mock-test workflow. A tester can upload the notes file, optionally provide the exam file as a style reference, then ask ARKAIS to create a mock test.

This is one of the clearest hackathon demo paths because it shows:

- grounded learning from uploaded material
- exam-style generation
- user-controlled structure
- downloadable study output

### Insights And Reports

The Insights view summarizes:

- mastery progress
- diagnostic coverage
- roadmap status
- material usage
- intervention risk
- next recommended learning step

It can also generate a weekly learning report and save it to Google Docs when Google saves is connected.

### Google Workspace Integration

ARKAIS uses MCP tools to connect learning actions to Google Workspace:

- Google Docs: save lessons, notes, reports, and assessments
- Google Tasks: create roadmap tasks or study tasks
- Google Calendar: schedule learning sessions
- Google Drive: save text exports

OAuth credentials are stored server-side, under each user record, so the app can perform Google actions only after the user connects Google saves.

### Authentication And Persistence

The frontend supports:

- Firebase Google Sign-In when configured
- server-side Firebase session cookies
- guest sessions for local demos
- email fallback for local development when Firebase web auth is not configured

Learner data is stored in Firestore when available, with SQLite fallback for local development.

## Current User Interface

The app is organized into four main views.

### Tutor

Main learning chat.

Key UI areas:

- chat messages
- starter prompts
- file attachment button
- voice status
- new session
- saved history
- learning focus panel
- mastery progress panel

Typical tester actions:

- "Teach me machine learning overfitting simply."
- "Quiz me on supervised vs unsupervised learning."
- "Continue my roadmap session."

### Plan

Diagnostics and roadmap generation.

Key UI areas:

- current roadmap summary
- diagnostic form
- roadmap builder
- calendar sync controls
- generated roadmap workspace
- previous roadmaps panel
- session status updates
- save roadmap tasks to Google Tasks
- save session reminders to Google Calendar

Typical tester actions:

- create a diagnostic for "machine learning"
- generate a 14-day beginner roadmap
- mark a roadmap session as complete
- open the roadmap workspace

### Materials

Study material uploads and mock-test creation.

Key UI areas:

- upload card
- file drop zone
- materials library
- selected material summary
- mock-test settings
- structure field
- sample exam style upload
- create mock test
- download mock test

Typical tester actions:

- upload `mock_ml_notes.md`
- upload or reference `mock_ml_exam.md` as sample exam style
- generate a mock test on introduction to machine learning

### Insights

Progress, risk, and reporting.

Key UI areas:

- learning signal panel
- refresh insights
- weekly report button
- evaluation snapshot
- next focus recommendations
- report workspace
- save report to Google Docs

Typical tester actions:

- refresh insights after a diagnostic or roadmap action
- generate a weekly report
- save the report to Google Docs if Google saves is connected

## Recommended Hackathon Testing Path

For judges, the fastest complete product walkthrough is:

1. Start the frontend.
2. Continue as guest or sign in with Google.
3. Ask the Tutor to explain a machine learning topic.
4. Open Plan and generate a diagnostic.
5. Generate a roadmap for "Introduction to Machine Learning."
6. Open Materials.
7. Upload `mock_ml_notes.md`.
8. Use `mock_ml_exam.md` as a sample exam style reference.
9. Generate a mock test.
10. Open Insights and refresh the learner snapshot.
11. Generate a weekly report.
12. Optional: connect Google saves and export the report or roadmap.

Full judge instructions are in [`HACKATHON_TESTER_GUIDE.md`](./HACKATHON_TESTER_GUIDE.md).

## Architecture Overview

```text
Learner Browser
    |
    v
Frontend UI: frontend/index.html, frontend/script.js, frontend/styles.css
    |
    v
FastAPI App: ark_learning_agent/main.py
    |
    v
Frontend API Router: ark_learning_agent/frontend_api.py
    |
    +--> Google ADK Runner + Root Agent: ark_learning_agent/agent.py
    |       |
    |       +--> Teaching Agent
    |       +--> Roadmap Agent
    |       +--> Evaluator Agent
    |       +--> Intervention Agent
    |       +--> Report Agent
    |
    +--> Learner State: ark_learning_agent/learner_state.py
    |
    +--> Materials: ark_learning_agent/materials.py
    |
    +--> Web Sessions: ark_learning_agent/web_session_store.py
    |
    +--> MCP Productivity Server: ark_learning_agent/productivity_mcp_server.py
            |
            +--> Google Docs
            +--> Google Calendar
            +--> Google Tasks
            +--> Google Drive

Persistence:
    Firestore in configured cloud environments
    SQLite fallback for local development

Auth:
    Firebase Auth for app identity
    Google OAuth callback for Workspace tool access
```

## Repository Structure

```text
.
├── ark_learning_agent/
│   ├── agent.py                    # Google ADK multi-agent definitions
│   ├── main.py                     # FastAPI app creation and ADK app mounting
│   ├── frontend_api.py             # Browser-facing API routes
│   ├── learner_state.py            # profiles, diagnostics, mastery, roadmaps, reports
│   ├── materials.py                # uploads, material context, mock-test generation
│   ├── web_session_store.py        # guest identity, chat sessions, chat messages
│   ├── productivity_mcp_server.py  # Google Docs, Tasks, Calendar, Drive MCP tools
│   ├── tools.py                    # ADK tool wrappers
│   └── demo_assets.py              # in-app demo/pitch data
├── auth_function/
│   └── main.py                     # Google OAuth callback handler
├── frontend/
│   ├── index.html                  # app markup
│   ├── script.js                   # frontend state and API calls
│   └── styles.css                  # UI styling
├── scripts/
│   ├── cleanup_expired_data.py     # retention cleanup
│   └── deploy_gcp.sh              # GCP deployment helper
├── tests/
│   └── test_frontend_server.py
├── mock_ml_notes.md                # judge/tester demo notes
├── mock_ml_exam.md                 # judge/tester exam-style reference
├── frontend_server.py              # local frontend server entrypoint
├── firestore.rules
├── firebase.json
├── Dockerfile
└── requirements.txt
```

## Important API Routes

The frontend communicates with FastAPI routes under `/api`.

### Session And Auth

- `GET /api/config`
- `GET /api/session`
- `POST /api/session`
- `POST /api/auth/session`
- `POST /api/auth/logout`

### Tutor Chat

- `POST /api/chat`
- `GET /api/chat/sessions`
- `GET /api/chat/messages`
- `POST /api/chat/delete`
- `POST /api/chat/delete-all`

### Diagnostics And Mastery

- `POST /api/diagnostic/start`
- `POST /api/diagnostic/submit`
- `GET /api/mastery`
- `GET /api/learner-state`

### Roadmaps

- `POST /api/roadmap/generate`
- `GET /api/roadmap`
- `GET /api/roadmaps`
- `POST /api/roadmap/session/update`
- `POST /api/roadmap/save-google-tasks`
- `POST /api/roadmap/session/save-calendar`
- `POST /api/roadmap/delete`

### Materials

- `GET /api/materials`
- `POST /api/materials/upload`
- `POST /api/materials/tutor`
- `POST /api/materials/mock-test`
- `POST /api/materials/delete`
- `POST /api/materials/delete-all`

### Insights And Reports

- `GET /api/intervention`
- `GET /api/evaluation`
- `POST /api/report/generate`
- `POST /api/report/save-google-doc`
- `POST /api/assessment/save-google-doc`

### Google Saves

- `GET /api/google/status`
- `POST /api/google/connect`
- `POST /api/google/connect-token`

## Local Setup

### Prerequisites

- Python 3.10 or newer
- pip
- optional: Google Cloud project
- optional: Firebase project
- optional: Google OAuth credentials for Docs, Drive, Calendar, and Tasks

For a local hackathon demo, Firebase and Google OAuth are optional. Without Firebase web config, ARKAIS falls back to guest sessions. Without Google OAuth, the learning features still work, but Google Workspace exports will not.

### 1. Create And Activate A Virtual Environment

From the repository root:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

If you run the ADK service directly from inside `ark_learning_agent`, install the agent requirements too:

```bash
pip install -r ark_learning_agent/requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the repo root or inside `ark_learning_agent/`.

Minimal local demo example:

```env
ARKAIS_FORCE_SQLITE=1
ARKAIS_ALLOW_EMAIL_FALLBACK_AUTH=1
GOOGLE_GENAI_USE_VERTEXAI=0
GEMINI_API_KEY=your-gemini-api-key
```

Google Cloud / Vertex AI example:

```env
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_API_KEY=your-firebase-web-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_APP_ID=your-firebase-web-app-id
```

Optional Firebase values:

```env
FIREBASE_MESSAGING_SENDER_ID=your-sender-id
FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
```

### 4. Start The Frontend

From the repo root:

```bash
python frontend_server.py
```

Open:

```text
http://127.0.0.1:4173
```

The frontend server uses port `4173` by default. To change it:

```powershell
$env:ARKAIS_FRONTEND_PORT="4174"
python frontend_server.py
```

### 5. Use Guest Mode Or Sign In

When the modal appears:

- choose Google Sign-In if Firebase web auth is configured
- otherwise continue as guest or use email fallback

Guest mode is enough for most hackathon testing.

## Google Workspace Setup

Google Workspace features require OAuth credentials and enabled Google APIs.

### Required APIs

Enable these APIs in the Google Cloud project:

- Google Docs API
- Google Drive API
- Google Calendar API
- Google Tasks API

### OAuth Credentials

Create an OAuth 2.0 Client ID for a web application in Google Cloud Console.

Add redirect URIs for your environment. Examples:

```text
http://localhost:8765/
https://your-auth-callback-service-url
```

For local development only, download the OAuth client JSON and save it as:

```text
ark_learning_agent/credentials.json
auth_function/credentials.json
```

These files are ignored by Git and should not be committed. For production deployment, prefer Secret Manager, mounted secrets, or deployment-time configuration rather than storing OAuth client files in the repository.

### OAuth Callback

The `auth_function/` service handles OAuth callbacks and stores the user's Google credentials in Firestore:

```text
users/{uid}/integrations/google_oauth
```

This keeps Google saves separate from normal Firebase web sign-in.

## Firestore Rules

This repo includes:

- [`firestore.rules`](./firestore.rules)
- [`firebase.json`](./firebase.json)

The rules assume:

- app data lives under `users/{uid}/...`
- signed-in Firebase users can only access their own user subtree
- service-managed Google OAuth records are denied from direct client access
- browser client records are service-managed

Deploy rules:

```bash
firebase deploy --only firestore:rules
```

## Retention And Cleanup

Guest users and chat history include `expires_at` fields.

Defaults:

- browser client identities: 30 days
- chat sessions: 90 days
- chat messages: 90 days

Override values:

```env
ARKAIS_BROWSER_CLIENT_RETENTION_DAYS=30
ARKAIS_CHAT_SESSION_RETENTION_DAYS=90
ARKAIS_CHAT_MESSAGE_RETENTION_DAYS=90
```

Dry-run cleanup:

```bash
python scripts/cleanup_expired_data.py
```

Apply cleanup:

```bash
python scripts/cleanup_expired_data.py --apply
```

For production, configure Firestore TTL policies on the `expires_at` field for:

- `users`
- `browser_clients`
- `chat_sessions`
- `messages`

## Cloud Run Deployment

The frontend can be deployed to Cloud Run. The top-level `Dockerfile` starts `frontend_server.py`, which serves both the static UI and API.

Local secret files such as `.env`, `credentials.json`, token files, SQLite databases, and uploaded learner materials are excluded from Docker and Cloud Build uploads by default. If production Google OAuth is required, provide credentials through a secure deployment mechanism instead of committing them.

### Required Google Cloud APIs

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

### Deploy Frontend Service

```bash
gcloud run deploy arkais-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=1
```

### One-Command Deployment Script

The repo also includes:

```text
scripts/deploy_gcp.sh
```

Prepare env:

```bash
cp deploy/.deploy.env.example deploy/.deploy.env
```

Edit `deploy/.deploy.env`, then run:

```bash
bash scripts/deploy_gcp.sh all
```

Deploy individual services:

```bash
bash scripts/deploy_gcp.sh auth
bash scripts/deploy_gcp.sh agent
bash scripts/deploy_gcp.sh frontend
```

## Testing

Run the available test suite:

```bash
pytest
```

For manual product testing, follow:

```text
HACKATHON_TESTER_GUIDE.md
```

## Demo Prompts

Useful Tutor prompts:

```text
Teach me overfitting in machine learning with one simple example.
```

```text
Quiz me on supervised, unsupervised, and reinforcement learning.
```

```text
Explain the machine learning pipeline in beginner-friendly terms.
```

Useful Roadmap inputs:

```text
Topic: Introduction to Machine Learning
Goal: Prepare for an exam
Level: Beginner
Study time: 1 hour per day
Deadline: 14 days
```

Useful Materials prompt:

```text
Using my uploaded notes, create a mock test that follows the uploaded exam style.
```

Useful Insights flow:

```text
Refresh insights after taking a diagnostic or generating a roadmap, then open the weekly report.
```

## Notes For Evaluators

Some features depend on external configuration:

- Gemini or Vertex AI credentials are required for live AI generation.
- Firebase web config is required for production Google Sign-In.
- Firestore is required for cloud persistence.
- Google OAuth credentials are required for Docs, Drive, Calendar, and Tasks.

If those are not configured, ARKAIS still supports a local guest demo using SQLite fallback, but Google Workspace save actions may return an auth or configuration message.

## Project Status

ARKAIS is a hackathon-ready prototype with an end-to-end learning workflow:

- tutor chat
- diagnostics
- mastery tracking
- roadmap generation
- materials upload
- mock-test generation
- insights and reports
- Google Workspace integration path

The included mock ML files are intentionally small so judges can test the materials and mock-test workflow quickly.