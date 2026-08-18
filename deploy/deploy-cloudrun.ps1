<#
.SYNOPSIS
    Deploy Picnic Raffle Manager to Google Cloud Run as a public demo (Windows).

.DESCRIPTION
    Cloud Run builds the Dockerfile with Cloud Build in GCP (no local Docker
    needed). Run this from PowerShell after installing the gcloud SDK and
    authenticating with `gcloud auth login`.

.EXAMPLE
    ./deploy/deploy-cloudrun.ps1

.EXAMPLE
    ./deploy/deploy-cloudrun.ps1 -ProjectId spiderfoot-419515 -Region us-central1 -AdminPin 8391
#>
param(
    [string]$ProjectId    = $(if ($env:PROJECT_ID) { $env:PROJECT_ID } else { "spiderfoot-419515" }),
    [string]$Region       = $(if ($env:REGION) { $env:REGION } else { "us-central1" }),
    [string]$Service      = "picnic-raffle",
    # A public demo lets anyone reach the volunteer screens (by design). Protect
    # the admin screens with a non-default PIN so visitors cannot close sales /
    # wipe data.
    [string]$AdminPin     = $(if ($env:ADMIN_PIN) { $env:ADMIN_PIN } else { "{0:D4}" -f (Get-Random -Maximum 10000) }),
    [string]$VolunteerPin = "0000",
    [string]$AppName      = "Picnic Raffle Manager (Demo)"
)

$ErrorActionPreference = "Stop"

# Repo root = parent of this script's directory.
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==> Project  : $ProjectId"
Write-Host "==> Region   : $Region"
Write-Host "==> Service  : $Service"
Write-Host "==> Admin PIN: $AdminPin   (save this - needed for /admin)"

Write-Host "==> Selecting project"
gcloud config set project $ProjectId

Write-Host "==> Enabling required APIs (run, cloudbuild, artifactregistry)"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

Write-Host "==> Deploying to Cloud Run (builds via Cloud Build)"
$envVars = "APP_NAME=$AppName,ADMIN_PIN=$AdminPin,VOLUNTEER_PIN=$VolunteerPin,DATABASE_URL=sqlite:////tmp/raffle.db,BACKUP_DIR=/tmp/backups,ENABLE_PERIODIC_BACKUP=false"
gcloud run deploy $Service `
    --source . `
    --region $Region `
    --allow-unauthenticated `
    --max-instances 1 `
    --min-instances 1 `
    --cpu 1 `
    --memory 512Mi `
    --timeout 3600 `
    --session-affinity `
    --set-env-vars $envVars

$url = gcloud run services describe $Service --region $Region --format "value(status.url)"
Write-Host ""
Write-Host "======================================================================"
Write-Host " Deployed:  $url"
Write-Host " Admin PIN: $AdminPin"
Write-Host ""
Write-Host " Next: open $url/admin/setup to run the wizard, or"
Write-Host "       $url/admin/prizes to import prizes, then open /display and /drawing."
Write-Host "======================================================================"
