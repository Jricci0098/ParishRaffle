#!/usr/bin/env bash
#
# Deploy Picnic Raffle Manager to Google Cloud Run as a public demo.
#
# Cloud Build builds the Dockerfile in GCP (no local Docker needed), so this
# works even where Docker Hub is unreachable locally.
#
# Prerequisites (one time):
#   - Install the gcloud SDK:  https://cloud.google.com/sdk/docs/install
#   - Authenticate:            gcloud auth login
#     (or:  gcloud auth activate-service-account --key-file=KEY.json)
#
# Usage:
#   ./deploy/deploy-cloudrun.sh
#   PROJECT_ID=spiderfoot-419515 REGION=us-central1 ADMIN_PIN=8391 \
#     ./deploy/deploy-cloudrun.sh
#
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-spiderfoot-419515}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-picnic-raffle}"
# A public demo lets anyone reach the volunteer screens (by design). Protect the
# admin screens with a non-default PIN so visitors cannot close sales / wipe data.
ADMIN_PIN="${ADMIN_PIN:-$(printf '%04d' $((RANDOM % 10000)))}"
VOLUNTEER_PIN="${VOLUNTEER_PIN:-0000}"
APP_NAME="${APP_NAME:-Picnic Raffle Manager (Demo)}"

# Repo root = parent of this script's directory.
cd "$(dirname "$0")/.."

echo "==> Project : $PROJECT_ID"
echo "==> Region  : $REGION"
echo "==> Service : $SERVICE"
echo "==> Admin PIN: $ADMIN_PIN   (save this — needed for /admin)"

echo "==> Selecting project"
gcloud config set project "$PROJECT_ID"

echo "==> Enabling required APIs (run, cloudbuild, artifactregistry)"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

echo "==> Deploying to Cloud Run (builds via Cloud Build)"
# Notes on the flags:
#  --max-instances 1 / --min-instances 1 : the app uses an in-process lock for
#    race-free ticket assignment and an in-memory SQLite DB, so it must run as a
#    single, always-on instance. (min 1 keeps data stable; set to 0 to save cost
#    at the price of the demo data resetting on a cold start.)
#  --timeout 3600 + --session-affinity : keep WebSocket connections alive and
#    pinned so live updates work.
#  DATABASE_URL/BACKUP_DIR under /tmp : the only reliably writable path.
gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --max-instances 1 \
  --min-instances 1 \
  --cpu 1 \
  --memory 512Mi \
  --timeout 3600 \
  --session-affinity \
  --set-env-vars "APP_NAME=$APP_NAME,ADMIN_PIN=$ADMIN_PIN,VOLUNTEER_PIN=$VOLUNTEER_PIN,DATABASE_URL=sqlite:////tmp/raffle.db,BACKUP_DIR=/tmp/backups,ENABLE_PERIODIC_BACKUP=false"

URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo
echo "======================================================================"
echo " Deployed:  $URL"
echo " Admin PIN: $ADMIN_PIN"
echo
echo " Next: open $URL/admin/setup to run the wizard, or"
echo "       $URL/admin/prizes to import prizes, then open /display and /drawing."
echo "======================================================================"
