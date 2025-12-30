#!/bin/bash

# Script to build and deploy the frontend to Firebase Hosting
# It fetches the Cloud Function URLs from Terraform outputs and populates the .env.production file

set -e

# Small helper: check if a terraform output exists
tf_has_output() {
  terraform output -json "$1" >/dev/null 2>&1
}

# Navigate to the tf directory to get outputs
cd "$(dirname "$0")/../tf"

echo "Fetching Terraform outputs..."

if ! tf_has_output "users_api_url" || ! tf_has_output "accounts_api_url" || ! tf_has_output "transactions_api_url"; then
  echo "ERROR: Missing backend outputs in Terraform state."
  echo "Run: (cd tf && terraform apply) first."
  exit 1
fi

if ! tf_has_output "firebase_config"; then
  echo "ERROR: Output \"firebase_config\" not found in Terraform state."
  echo "You likely changed Terraform but haven't applied it yet."
  echo "Run: (cd tf && terraform apply) first."
  exit 1
fi

if ! tf_has_output "firebase_web_config"; then
  echo "ERROR: Output \"firebase_web_config\" not found in Terraform state."
  echo "Run: (cd tf && terraform apply) first."
  exit 1
fi

USERS_API_URL=$(terraform output -raw users_api_url)
ACCOUNTS_API_URL=$(terraform output -raw accounts_api_url)
TRANSACTIONS_API_URL=$(terraform output -raw transactions_api_url)

export FIREBASE_CONFIG_JSON
FIREBASE_CONFIG_JSON=$(terraform output -json firebase_config)
PROJECT_ID=$(python3 - <<PY
import json, os
print(json.loads(os.environ["FIREBASE_CONFIG_JSON"])["projectId"])
PY
)
APP_ID=$(python3 - <<PY
import json, os
print(json.loads(os.environ["FIREBASE_CONFIG_JSON"])["appId"])
PY
)

# Full Firebase web config from Terraform (no manual filling required)
export FIREBASE_WEB_CONFIG_JSON
FIREBASE_WEB_CONFIG_JSON=$(terraform output -json firebase_web_config)
FIREBASE_API_KEY=$(python3 - <<PY
import json, os
print(json.loads(os.environ["FIREBASE_WEB_CONFIG_JSON"])["apiKey"])
PY
)
FIREBASE_AUTH_DOMAIN=$(python3 - <<PY
import json, os
print(json.loads(os.environ["FIREBASE_WEB_CONFIG_JSON"])["authDomain"])
PY
)
FIREBASE_STORAGE_BUCKET=$(python3 - <<PY
import json, os
print(json.loads(os.environ["FIREBASE_WEB_CONFIG_JSON"])["storageBucket"])
PY
)
FIREBASE_MESSAGING_SENDER_ID=$(python3 - <<PY
import json, os
print(json.loads(os.environ["FIREBASE_WEB_CONFIG_JSON"])["messagingSenderId"])
PY
)

# Navigate back to frontend
cd ../frontend

echo "Preparing build environment..."
# Avoid relying on .env files (some environments block reading them). We pass VITE_* via process env.
rm -f .env .env.production .env.production.local .env.local 2>/dev/null || true

export VITE_USERS_API_URL="${USERS_API_URL}"
export VITE_ACCOUNTS_API_URL="${ACCOUNTS_API_URL}"
export VITE_TRANSACTIONS_API_URL="${TRANSACTIONS_API_URL}"
export VITE_FIREBASE_API_KEY="${FIREBASE_API_KEY}"
export VITE_FIREBASE_AUTH_DOMAIN="${FIREBASE_AUTH_DOMAIN}"
export VITE_FIREBASE_PROJECT_ID="${PROJECT_ID}"
export VITE_FIREBASE_STORAGE_BUCKET="${FIREBASE_STORAGE_BUCKET}"
export VITE_FIREBASE_MESSAGING_SENDER_ID="${FIREBASE_MESSAGING_SENDER_ID}"
export VITE_FIREBASE_APP_ID="${APP_ID}"

echo "Using Firebase project: ${PROJECT_ID}"
echo "Using Firebase authDomain: ${FIREBASE_AUTH_DOMAIN}"
if [ -z "${VITE_FIREBASE_API_KEY}" ] || [ "${VITE_FIREBASE_API_KEY}" = "null" ]; then
  echo "ERROR: VITE_FIREBASE_API_KEY is empty. Terraform output firebase_web_config is missing/invalid."
  echo "Run: (cd tf && terraform apply) then retry."
  exit 1
fi

echo "Building frontend..."
npm install
npm run build

echo "Deploying to Firebase Hosting..."
if command -v firebase >/dev/null 2>&1; then
  firebase deploy --only hosting --project "${PROJECT_ID}"
else
  echo "Firebase CLI not found. Using npx firebase-tools..."
  npx --yes firebase-tools deploy --only hosting --project "${PROJECT_ID}"
fi

echo "Done!"

