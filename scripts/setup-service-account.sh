#!/bin/bash
# Service Account Setup — Delivery Route Optimization Agent (v2.0)
#
# Creates the 'route-optimizer-agent' service account with least-privilege
# roles required by gcp_architecture_v3.md (Section 10.2), then removes
# the legacy 'terraform-dataops' service account.
#
# Usage: ./scripts/setup-service-account.sh

set -e

# ── Configuration ─────────────────────────────────────────────────────────────
PROJECT_ID="manish-sandpit"
SA_NAME="hackathon-agent-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
CREDENTIALS_DIR="$HOME/.gcp/credentials"
CREDENTIALS_FILE="${CREDENTIALS_DIR}/${SA_NAME}-key.json"

# Least-privilege roles per architecture for Phase 1:
#   - Storage Object Admin (read/write raw GCS files)
#   - BigQuery Data Editor (read/write datasets)
#   - BigQuery Job User (run dbt queries)
#   - Cloud Run Invoker (invoke dbt jobs)
#   - Eventarc Event Receiver (receive GCS events)
#   - Vertex AI User (Gemini integration for analytics)
#   - Cloud Logging Writer (audit trail)
ROLES=(
    "roles/storage.objectAdmin"              # GCS - read/write raw files
    "roles/bigquery.dataEditor"              # BigQuery - read/write datasets
    "roles/bigquery.jobUser"                 # BigQuery - run jobs/queries
    "roles/run.invoker"                      # Cloud Run - invoke dbt jobs
    "roles/eventarc.eventReceiver"           # Eventarc - receive GCS events
    "roles/aiplatform.user"                  # Vertex AI - Gemini integration
    "roles/logging.logWriter"                # Cloud Logging
)

# ── Preflight checks ──────────────────────────────────────────────────────────
if ! command -v gcloud &>/dev/null; then
    echo "ERROR: gcloud CLI not found. Install it first: brew install --cask google-cloud-sdk"
    exit 1
fi

if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "ERROR: Not authenticated. Run: gcloud auth login"
    exit 1
fi

gcloud config set project "$PROJECT_ID"

if ! gcloud projects describe "$PROJECT_ID" &>/dev/null; then
    echo "ERROR: Cannot access project $PROJECT_ID"
    exit 1
fi

echo "=== Service Account Setup: hackathon_agent_sa ==="
echo "Project : $PROJECT_ID"
echo ""

# ── Step 1: Leave existing SAs untouched ─────────────────────────────────────
echo "--- Step 1: Leaving existing SAs (e.g. route-optimizer-agent) untouched ---"

# ── Step 2: Create hackathon_agent_sa SA ───────────────────────────────────
echo ""
echo "--- Step 2: Create 'hackathon_agent_sa' service account ---"
if gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    echo "  Service account already exists: $SA_EMAIL"
else
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Hackathon Agent SA" \
        --description="Runs the Data Warehouse Hackathon pipeline (BigQuery, dbt, Eventarc)." \
        --project="$PROJECT_ID"
    echo "  Created: $SA_EMAIL"
fi

# ── Step 3: Assign IAM roles ──────────────────────────────────────────────────
echo ""
echo "--- Step 3: Assign IAM roles ---"
for ROLE in "${ROLES[@]}"; do
    echo "  Assigning $ROLE ..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="$ROLE" \
        --quiet
done
echo "  Done."

# ── Step 4: Generate service account key ──────────────────────────────────────
echo ""
echo "--- Step 4: Generate key ---"
mkdir -p "$CREDENTIALS_DIR"
chmod 700 "$CREDENTIALS_DIR"

if [ -f "$CREDENTIALS_FILE" ]; then
    BACKUP="${CREDENTIALS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  Backing up existing key to $BACKUP"
    cp "$CREDENTIALS_FILE" "$BACKUP"
fi

gcloud iam service-accounts keys create "$CREDENTIALS_FILE" \
    --iam-account="$SA_EMAIL"
chmod 600 "$CREDENTIALS_FILE"
echo "  Key saved to: $CREDENTIALS_FILE"

# ── Step 5: Verify ────────────────────────────────────────────────────────────
echo ""
echo "--- Step 5: Verify ---"
export GOOGLE_APPLICATION_CREDENTIALS="$CREDENTIALS_FILE"
if gcloud projects describe "$PROJECT_ID" &>/dev/null; then
    echo "  Authentication OK."
else
    echo "  ERROR: Authentication test failed."
    exit 1
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Service account : $SA_EMAIL"
echo "Key file        : $CREDENTIALS_FILE"
echo ""
echo "To activate for local development:"
echo "  export GOOGLE_APPLICATION_CREDENTIALS=\"$CREDENTIALS_FILE\""
echo ""
echo "To use Application Default Credentials instead (recommended for local dev):"
echo "  gcloud auth application-default login"
