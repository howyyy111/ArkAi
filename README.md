# ARKAIS

ARKAIS is an intelligent, AI-driven learning and teaching assistant built leveraging the Google Agent Development Kit (ADK) and the Model Context Protocol (MCP). It acts as a personal tutor that adapts to your learning style, creates structured study roadmaps, and seamlessly integrates with your Google Workspace to organize your educational journey.

## 🌟 Features

*   **Teaching Agent:** Delivers short, practical, and highly focused lessons tailored to your available time and learning preferences. It explains concepts, provides examples, sets up short coding tasks or quizzes, and tracks your progress.
*   **Roadmap Agent:** Acts as a study planner that breaks down larger goals into structured weekly phases and tangible outcomes.
*   **Google Workspace Integration (MCP):** Connects with your Google account to enhance productivity:
    *   **Google Docs:** Automatically saves thorough summaries and code examples directly to your Drive.
    *   **Google Calendar:** Schedules follow-up lessons, checks your timezone, and adds learning sessions to your calendar.
    *   **Google Tasks:** Adds homework and study tasks.
*   **Persistent Progress Tracking:** Stores learner profiles, learning patterns, learner state, notes, and historical progress in Firebase Firestore, with SQLite fallback for local-only development.
*   **Firebase Auth Ready Frontend:** Supports Google Sign-In on the web UI and uses the same learner identity across chat, persistence, and Google Workspace actions.
*   **Diagnostics And Mastery Engine:** Generates short diagnostics, scores quiz attempts, tracks concept weaknesses, and updates topic mastery over time.
*   **Living Roadmaps:** Generates milestone-based study plans with checkpoints, tracks session completion, and automatically switches into recovery mode when the learner falls behind.
*   **Grounded Materials Library:** Supports uploading notes, code/text files, and study images for grounded tutoring with source-aware answers.
*   **Voice And Multimodal Tutoring:** Adds browser voice input/output for hands-free tutoring and image-aware study help when Gemini multimodal support is available.
*   **Evaluation And Intervention Agents:** Adds dedicated progress-review, recovery-planning, and reporting flows on top of the tutor and roadmap agents.
*   **Google Workflow Actions:** Can save weekly reports to Google Docs and create Google Tasks directly from the learner's active roadmap.
*   **Dashboard UX:** Surfaces mastery, roadmap momentum, grounded materials, intervention risk, and weekly insights in a single learner cockpit.
*   **Architecture Readiness View:** Exposes Firebase/Auth/Vertex/OAuth/runtime readiness and lightweight in-app metrics for demo and deployment confidence.
*   **Judge Demo Kit:** Includes demo personas, measurable learner metrics, a polished end-to-end demo script, and a concise pitch inside the product UI.

## 🏗️ Architecture

The project is split into two main components:

1.  **`ark_learning_agent/`**: Contains the core logic for the ADK Agents (`teaching_agent` and `roadmap_agent`) and the FastMCP server (`productivity_mcp_server.py`). The MCP server securely manages tools that interact with Google APIs and local/remote databases.
2.  **`auth_function/`**: A Google Cloud HTTP Function that handles the OAuth 2.0 callback flow. This service securely receives Google authorization codes, exchanges them for tokens, and securely stores the credentials in Firebase Firestore for the agents to use on behalf of the user.

## 🚀 Setup & Installation

### Prerequisites
*   Python 3.10+
*   A Google Cloud Project with the following APIs enabled:
    *   Google Calendar API
    *   Google Tasks API
    *   Google Docs API
    *   Google Drive API
*   Firebase initialized in your GCP project (Firestore database).

### 1. Configure the Agent Environment

Navigate to the `ark_learning_agent` directory and configure the environment:

```bash
cd ark_learning_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create or update the `.env` file in this directory based on your Google Cloud environment:

```env
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_API_KEY=your-firebase-web-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_APP_ID=your-firebase-web-app-id
# Optional:
# FIREBASE_MESSAGING_SENDER_ID=...
# FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
```

If the Firebase web variables are not set, the frontend falls back to a Gmail prompt for local demos.
If you want to force local persistence during development, set `ARKAIS_FORCE_SQLITE=1`.

Supported local material upload types in the current prototype:

*   Text and notes: `.txt`, `.md`, `.csv`, `.json`, `.html`, `.css`, `.js`, `.py`
*   Images for multimodal tutoring: `.png`, `.jpg`, `.jpeg`, `.webp`

### 2. Configure Google OAuth Credentials

1.  In your GCP Console, go to **APIs & Services** > **Credentials**.
2.  Create an **OAuth 2.0 Client ID** (Web application).
3.  Add your redirect URIs (e.g., `http://localhost:8765/` for local testing, or the URL of your deployed `auth_function`).
4.  Download the JSON file and save it as `credentials.json` in **both** the `ark_learning_agent/` and `auth_function/` directories.

### 3. Deploy the Auth Function (Optional / Production)

If running in the cloud, you can deploy the webhook to GCP Cloud Functions:

```bash
cd auth_function
gcloud functions deploy auth_callback \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --project your-project-id \
  --region us-central1
```

Ensure that the resulting trigger URL matches the redirect URI specified in your `credentials.json` and GCP Console.

## 💻 Usage

To start interacting with the agents:

1.  Ensure you have initialized your Python environment and the SQLite/Firestore databases are accessible.
2.  Run the agent application. The MCP Server will launch internally as a subprocess.
3.  Whenever the agents attempt to interact with Google Workspace tools for the first time, you will be provided with an OAuth authorization URL (if an active Firebase token is not found using your username).
4.  Click the authorization link, approve the required scopes, and the `auth_function` will catch the redirect, saving your secure token centrally.

## 🖥️ Minimal Frontend

A simple static frontend is available in [`frontend/`](./frontend) for a lightweight local UI prototype.

Run the connected frontend from the repo root:

```bash
python3 frontend_server.py
```

Then open `http://127.0.0.1:4173`.

The frontend server uses port `4173` by default so it does not clash with a service already using port `8000`. You can override it with `ARKAIS_FRONTEND_PORT`.

This frontend currently provides:

*   A minimal ARKAIS chat interface
*   Firebase Auth based Google Sign-In when configured, with Gmail fallback for local demos
*   A study console that sends requests to the local Python ADK agent via `/api/chat`
*   A learner-state strip showing the current topic, activity count, and next recommended action
*   A diagnostic panel that generates a short assessment, scores it, and updates the mastery board
*   A roadmap panel that creates milestone-based plans, tracks session progress, and triggers recovery rebuilds
*   A materials panel for uploads, grounded Q&A, and source selection
*   Browser voice controls for dictation and spoken tutor replies
*   An insights panel for intervention risk, evaluation coverage, and weekly report generation
*   A dashboard overview with key learner metrics and quick section navigation
*   An architecture panel with Google-native readiness and runtime metrics
*   A judge demo kit panel with personas, pitch copy, demo metrics, and presentation steps

It serves the static files and API from the same local server, so no extra frontend tooling is required.

## ☁️ Deploy Frontend To Cloud Run

The frontend can be deployed as its own Cloud Run service directly from this repo.

### What this deploys

This deploy runs [`frontend_server.py`](./frontend_server.py), which:

*   Serves the static frontend
*   Exposes `/api/chat`
*   Calls the local Python ADK agent inside the same Cloud Run container

### Before you deploy

1.  Install and authenticate the Google Cloud CLI:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

2.  Enable the required APIs:

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

3.  Make sure your runtime configuration exists for the agent:

*   Required environment variables such as `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and `GOOGLE_GENAI_USE_VERTEXAI`
*   Your `ark_learning_agent/credentials.json` if you want Google Docs / Calendar / Tasks OAuth flows to work from this service

### Deploy command

From the repo root, run:

```bash
gcloud run deploy arkais-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=1
```

Replace `YOUR_PROJECT_ID` with your real Google Cloud project ID.

### If you need credentials.json in Cloud Run

If this service needs Google OAuth tool access, the container must include the same OAuth client config expected by the agent. The simplest approach is:

1.  Put `credentials.json` in [`ark_learning_agent/`](./ark_learning_agent)
2.  Deploy from source so the file is included in the built image

If you do not need Google Docs / Calendar / Tasks yet, you can deploy without it.

### After deploy

1.  Wait for the build and deploy to finish
2.  Open the Cloud Run service URL shown by `gcloud`
3.  Enter a username in the frontend modal
4.  Start chatting with the agent

### Notes

*   Cloud Run requires the service to listen on the `PORT` environment variable. [`frontend_server.py`](./frontend_server.py) now supports that.
*   This repo now includes a top-level [`Dockerfile`](./Dockerfile) so Cloud Run deploys the correct app entrypoint: `python3 frontend_server.py`.
*   Without that explicit container entrypoint, Cloud Run source deploy may auto-detect and start the Google ADK FastAPI runtime instead of the frontend server.

## 🔧 One-Command GCP Deploy

A repo-level deploy script is included at [`scripts/deploy_gcp.sh`](./scripts/deploy_gcp.sh). It will:

*   enable the required Google Cloud APIs
*   deploy the OAuth callback as its own Cloud Run service
*   deploy `ark_learning_agent` as its own Cloud Run service
*   capture the callback URL and agent URL automatically
*   deploy the frontend server to Cloud Run with matching `AUTH_CALLBACK_URL` and `ARKAIS_AGENT_API_URL`

### 1. Prepare the deploy env file

```bash
cp deploy/.deploy.env.example deploy/.deploy.env
```

Edit [`deploy/.deploy.env`](./deploy/.deploy.env) with your real project and Firebase values.

### 2. Make sure OAuth credentials are present

These files should exist before deploying:

*   [`ark_learning_agent/credentials.json`](./ark_learning_agent/credentials.json)
*   [`auth_function/credentials.json`](./auth_function/credentials.json)

### 3. Run the full deploy

```bash
bash scripts/deploy_gcp.sh all
```

### 4. Deploy pieces separately if needed

Deploy only the OAuth callback:

```bash
bash scripts/deploy_gcp.sh auth
```

Deploy only the standalone agent:

```bash
bash scripts/deploy_gcp.sh agent
```

Deploy only the frontend service:

```bash
bash scripts/deploy_gcp.sh frontend
```

The script prints the auth callback URL, standalone agent URL, and frontend URL when deployment succeeds.

If your existing Cloud Run auth callback service is named `auth-function`, set:

```bash
AUTH_SERVICE_NAME=auth-function
```

*Happy Learning with ARKAIS!*
