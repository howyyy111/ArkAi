#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_ENV_FILE="${DEPLOY_ENV_FILE:-$ROOT_DIR/deploy/.deploy.env}"
MODE="${1:-all}"

if [[ "$MODE" != "all" && "$MODE" != "frontend" && "$MODE" != "auth" && "$MODE" != "agent" ]]; then
  echo "Usage: $0 [all|frontend|auth|agent]"
  exit 1
fi

if [[ ! -f "$DEPLOY_ENV_FILE" ]]; then
  echo "Missing deploy env file: $DEPLOY_ENV_FILE"
  echo "Copy $ROOT_DIR/deploy/.deploy.env.example to $DEPLOY_ENV_FILE and fill it in."
  exit 1
fi

set -a
source "$DEPLOY_ENV_FILE"
set +a

PROJECT_ID="${PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-}}"
REGION="${REGION:-${GOOGLE_CLOUD_LOCATION:-us-central1}}"
FRONTEND_SERVICE_NAME="${FRONTEND_SERVICE_NAME:-${SERVICE_NAME:-arkais-frontend}}"
AGENT_SERVICE_NAME="${AGENT_SERVICE_NAME:-ark-learning-agent}"
AUTH_SERVICE_NAME="${AUTH_SERVICE_NAME:-${AUTH_FUNCTION_NAME:-auth-function}}"
RUNTIME_SERVICE_ACCOUNT="${RUNTIME_SERVICE_ACCOUNT:-}"
GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-1}"
FIREBASE_PROJECT_ID="${FIREBASE_PROJECT_ID:-$PROJECT_ID}"
GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-$REGION}"
GOOGLE_OAUTH_PROMPT="${GOOGLE_OAUTH_PROMPT:-select_account consent}"
ALLOW_UNAUTHENTICATED="${ALLOW_UNAUTHENTICATED:-true}"
ARKAIS_AGENT_WITH_UI="${ARKAIS_AGENT_WITH_UI:-true}"
DEPLOY_AGENT_SERVICE="${DEPLOY_AGENT_SERVICE:-false}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID is required in $DEPLOY_ENV_FILE"
  exit 1
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1"
    exit 1
  fi
}

require_cmd gcloud
require_cmd python3

if [[ ! -f "$ROOT_DIR/ark_learning_agent/credentials.json" ]]; then
  echo "Warning: missing $ROOT_DIR/ark_learning_agent/credentials.json"
  echo "Google Docs / Calendar / Tasks OAuth will not work from the standalone agent service."
fi

if [[ ! -f "$ROOT_DIR/auth_function/credentials.json" ]]; then
  echo "Warning: missing $ROOT_DIR/auth_function/credentials.json"
  echo "The auth callback service will not be able to exchange Google auth codes without it."
fi

echo "Using project: $PROJECT_ID"
echo "Using region:  $REGION"

gcloud config set project "$PROJECT_ID" >/dev/null

echo "Enabling required Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  cloudfunctions.googleapis.com \
  firestore.googleapis.com \
  firebase.googleapis.com \
  eventarc.googleapis.com \
  logging.googleapis.com \
  --project "$PROJECT_ID" >/dev/null

AUTH_URL=""
AGENT_URL=""
FRONTEND_URL=""

deploy_auth() {
  echo "Deploying auth callback service: $AUTH_SERVICE_NAME"

  local env_file
  env_file="$(mktemp)"
  cat >"$env_file" <<EOF
GOOGLE_CLOUD_PROJECT: "$PROJECT_ID"
GCLOUD_PROJECT: "$PROJECT_ID"
FIREBASE_PROJECT_ID: "$FIREBASE_PROJECT_ID"
EOF

  if [[ -n "${OAUTH_REDIRECT_URI:-}" ]]; then
    cat >>"$env_file" <<EOF
OAUTH_REDIRECT_URI: "${OAUTH_REDIRECT_URI}"
AUTH_CALLBACK_URL: "${OAUTH_REDIRECT_URI}"
EOF
  fi

  local deploy_cmd=(
    gcloud run deploy "$AUTH_SERVICE_NAME"
    --source "$ROOT_DIR/auth_function"
    --region "$REGION"
    --clear-base-image
    --env-vars-file "$env_file"
    --project "$PROJECT_ID"
  )

  if [[ "$ALLOW_UNAUTHENTICATED" == "true" ]]; then
    deploy_cmd+=(--allow-unauthenticated)
  fi

  if [[ -n "$RUNTIME_SERVICE_ACCOUNT" ]]; then
    deploy_cmd+=(--service-account "$RUNTIME_SERVICE_ACCOUNT")
  fi

  "${deploy_cmd[@]}"
  rm -f "$env_file"

  AUTH_URL="$(
    gcloud run services describe "$AUTH_SERVICE_NAME" \
      --region "$REGION" \
      --project "$PROJECT_ID" \
      --format='value(status.url)'
  )"

  if [[ -z "$AUTH_URL" ]]; then
    echo "Could not resolve auth callback URL after deployment."
    exit 1
  fi

  echo "Auth callback URL: $AUTH_URL"
}

deploy_agent() {
  echo "Deploying standalone agent service: $AGENT_SERVICE_NAME"

  local env_file
  env_file="$(mktemp)"
  cat >"$env_file" <<EOF
GOOGLE_CLOUD_PROJECT: "$PROJECT_ID"
GCLOUD_PROJECT: "$PROJECT_ID"
GOOGLE_CLOUD_LOCATION: "$GOOGLE_CLOUD_LOCATION"
GOOGLE_GENAI_USE_VERTEXAI: "$GOOGLE_GENAI_USE_VERTEXAI"
FIREBASE_PROJECT_ID: "$FIREBASE_PROJECT_ID"
AUTH_CALLBACK_URL: "$AUTH_URL"
GOOGLE_OAUTH_PROMPT: "$GOOGLE_OAUTH_PROMPT"
ARKAIS_AGENT_WITH_UI: "$ARKAIS_AGENT_WITH_UI"
EOF

  local deploy_cmd=(
    gcloud run deploy "$AGENT_SERVICE_NAME"
    --source "$ROOT_DIR/ark_learning_agent"
    --region "$REGION"
    --clear-base-image
    --env-vars-file "$env_file"
    --project "$PROJECT_ID"
  )

  if [[ "$ALLOW_UNAUTHENTICATED" == "true" ]]; then
    deploy_cmd+=(--allow-unauthenticated)
  fi

  if [[ -n "$RUNTIME_SERVICE_ACCOUNT" ]]; then
    deploy_cmd+=(--service-account "$RUNTIME_SERVICE_ACCOUNT")
  fi

  "${deploy_cmd[@]}"
  rm -f "$env_file"

  AGENT_URL="$(
    gcloud run services describe "$AGENT_SERVICE_NAME" \
      --region "$REGION" \
      --project "$PROJECT_ID" \
      --format='value(status.url)'
  )"

  if [[ -z "$AGENT_URL" ]]; then
    echo "Could not resolve agent URL after deployment."
    exit 1
  fi

  echo "Agent URL: $AGENT_URL"
}

resolve_auth_url() {
  if [[ -n "${AUTH_CALLBACK_URL:-}" ]]; then
    AUTH_URL="${AUTH_CALLBACK_URL}"
    return
  fi

  AUTH_URL="$(
    gcloud run services describe "$AUTH_SERVICE_NAME" \
      --region "$REGION" \
      --project "$PROJECT_ID" \
      --format='value(status.url)' 2>/dev/null || true
  )"
}

resolve_agent_url() {
  if [[ -n "${ARKAIS_AGENT_API_URL:-}" ]]; then
    AGENT_URL="${ARKAIS_AGENT_API_URL}"
    return
  fi

  AGENT_URL="$(
    gcloud run services describe "$AGENT_SERVICE_NAME" \
      --region "$REGION" \
      --project "$PROJECT_ID" \
      --format='value(status.url)' 2>/dev/null || true
  )"
}

deploy_frontend() {
  echo "Deploying frontend service: $FRONTEND_SERVICE_NAME"

  local env_file
  env_file="$(mktemp)"
  cat >"$env_file" <<EOF
GOOGLE_CLOUD_PROJECT: "$PROJECT_ID"
GCLOUD_PROJECT: "$PROJECT_ID"
GOOGLE_CLOUD_LOCATION: "$GOOGLE_CLOUD_LOCATION"
GOOGLE_GENAI_USE_VERTEXAI: "$GOOGLE_GENAI_USE_VERTEXAI"
FIREBASE_PROJECT_ID: "$FIREBASE_PROJECT_ID"
FIREBASE_API_KEY: "${FIREBASE_API_KEY:-}"
FIREBASE_AUTH_DOMAIN: "${FIREBASE_AUTH_DOMAIN:-}"
FIREBASE_APP_ID: "${FIREBASE_APP_ID:-}"
FIREBASE_MESSAGING_SENDER_ID: "${FIREBASE_MESSAGING_SENDER_ID:-}"
FIREBASE_STORAGE_BUCKET: "${FIREBASE_STORAGE_BUCKET:-}"
AUTH_CALLBACK_URL: "$AUTH_URL"
GOOGLE_OAUTH_PROMPT: "$GOOGLE_OAUTH_PROMPT"
ARKAIS_FRONTEND_HOST: "0.0.0.0"
EOF

  if [[ -n "$AGENT_URL" ]]; then
    cat >>"$env_file" <<EOF
ARKAIS_AGENT_API_URL: "$AGENT_URL"
ARKAIS_AGENT_APP_NAME: "ark_learning_agent"
EOF
  fi

  if [[ -n "${ARKAIS_AGENT_TIMEOUT_SECONDS:-}" ]]; then
    cat >>"$env_file" <<EOF
ARKAIS_AGENT_TIMEOUT_SECONDS: "${ARKAIS_AGENT_TIMEOUT_SECONDS}"
EOF
  fi

  local deploy_cmd=(
    gcloud run deploy "$FRONTEND_SERVICE_NAME"
    --source "$ROOT_DIR"
    --region "$REGION"
    --clear-base-image
    --env-vars-file "$env_file"
    --project "$PROJECT_ID"
  )

  if [[ "$ALLOW_UNAUTHENTICATED" == "true" ]]; then
    deploy_cmd+=(--allow-unauthenticated)
  fi

  if [[ -n "$RUNTIME_SERVICE_ACCOUNT" ]]; then
    deploy_cmd+=(--service-account "$RUNTIME_SERVICE_ACCOUNT")
  fi

  "${deploy_cmd[@]}"
  rm -f "$env_file"

  FRONTEND_URL="$(
    gcloud run services describe "$FRONTEND_SERVICE_NAME" \
      --region "$REGION" \
      --project "$PROJECT_ID" \
      --format='value(status.url)'
  )"

  echo "Frontend URL: $FRONTEND_URL"
}

case "$MODE" in
  auth)
    deploy_auth
    ;;
  agent)
    resolve_auth_url
    if [[ -z "$AUTH_URL" ]]; then
      echo "No auth callback URL found. Deploy auth first with:"
      echo "  $0 auth"
      exit 1
    fi
    deploy_agent
    ;;
  frontend)
    resolve_auth_url
    if [[ -z "$AUTH_URL" ]]; then
      echo "No auth callback URL found. Deploy auth first with:"
      echo "  $0 auth"
      exit 1
    fi
    resolve_agent_url
    deploy_frontend
    ;;
  all)
    deploy_auth
    if [[ "$DEPLOY_AGENT_SERVICE" == "true" ]]; then
      deploy_agent
    else
      resolve_agent_url
    fi
    deploy_frontend
    ;;
esac
