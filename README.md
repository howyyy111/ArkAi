# ARKAIS

ARKAIS is an intelligent, AI-driven learning and teaching assistant built leveraging the Google Agent Development Kit (ADK) and the Model Context Protocol (MCP). It acts as a personal tutor that adapts to your learning style, creates structured study roadmaps, and seamlessly integrates with your Google Workspace to organize your educational journey.

## 🌟 Features

*   **Teaching Agent:** Delivers short, practical, and highly focused lessons tailored to your available time and learning preferences. It explains concepts, provides examples, sets up short coding tasks or quizzes, and tracks your progress.
*   **Roadmap Agent:** Acts as a study planner that breaks down larger goals into structured weekly phases and tangible outcomes.
*   **Google Workspace Integration (MCP):** Connects with your Google account to enhance productivity:
    *   **Google Docs:** Automatically saves thorough summaries and code examples directly to your Drive.
    *   **Google Calendar:** Schedules follow-up lessons, checks your timezone, and adds learning sessions to your calendar.
    *   **Google Tasks:** Adds homework and study tasks.
*   **Persistent Progress Tracking:** Stores learner profiles, learning patterns, and historical progress locally (SQLite) or in the cloud (Firebase Firestore).

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
```

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
*   A username prompt stored in the browser for chat identity
*   A study console that sends requests to the local Python ADK agent via `/api/chat`

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
*   Source deploy with `gcloud run deploy --source .` is supported by Google Cloud Run and uses Cloud Build/buildpacks automatically. See Google’s official docs: [Deploy services from source code](https://cloud.google.com/run/docs/deploying-source-code), [Python buildpack entrypoints](https://cloud.google.com/docs/buildpacks/python), and [Procfile support](https://docs.cloud.google.com/docs/buildpacks/about-procfile).

*Happy Learning with ARKAIS!*
