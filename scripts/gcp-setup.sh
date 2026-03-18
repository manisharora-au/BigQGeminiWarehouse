#!/bin/bash
# GCP Project Setup Script — Delivery Route Optimization Agent (v2.0)
# Enables only the APIs required by the architecture (gcp_architecture_v3.md).
# Run this once per project before deploying infrastructure.

set -e

PROJECT_ID="manish-sandpit"
REGION="us-central1"

echo "=== GCP Setup: Delivery Route Optimization Agent ==="
echo "Project : $PROJECT_ID"
echo "Region  : $REGION"
echo ""

# Set project defaults
gcloud config set project "$PROJECT_ID"
gcloud config set compute/region "$REGION"

echo ""
echo "=== Enabling required APIs ==="

# APIs required by the architecture
APIS=(
    # Core runtime & triggering
    "run.googleapis.com"                      # Cloud Run Jobs — dbt orchestration
    "eventarc.googleapis.com"                 # Eventarc — GCS triggers for Cloud Run

    # AI & ML
    "aiplatform.googleapis.com"               # Vertex AI — Gemini, Conversational Analytics

    # Data stores & Analytics
    "storage.googleapis.com"                  # Cloud Storage — raw data
    "bigquery.googleapis.com"                 # BigQuery — analytics warehouse + BigQuery ML

    # Governance & Metadata
    "dataplex.googleapis.com"                 # Dataplex — data catalogue, data lineage, quality

    # Observability
    "logging.googleapis.com"               # Cloud Logging — audit trail
    "monitoring.googleapis.com"            # Cloud Monitoring — alerts and metrics

    # IAM & resource management
    "iam.googleapis.com"                   # IAM — service accounts
    "cloudresourcemanager.googleapis.com"  # Resource management
)

for api in "${APIS[@]}"; do
    # Skip comment lines (lines starting with #)
    [[ "$api" == \#* ]] && continue
    echo "  Enabling $api ..."
    gcloud services enable "$api" --quiet
done

echo ""
echo "=== Enabled APIs (verification) ==="
gcloud services list --enabled --format="table(name)" | grep -E \
    "run|aiplatform|eventarc|storage|bigquery|dataplex|logging|monitoring|iam|cloudresourcemanager"

echo ""
echo "=== Setup complete ==="
echo "Next: run scripts/setup-service-account.sh to create the route-optimizer-agent SA."
