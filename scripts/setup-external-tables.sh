#!/bin/bash
# Setup BigQuery External Tables — BigQuery Gemini Warehouse
#
# Creates external tables in the 'raw_ext' dataset pointing to CSV files in GCS.
#
# Usage: ./scripts/setup-external-tables.sh

set -e

# ── Configuration ─────────────────────────────────────────────────────────────
PROJECT_ID="manish-sandpit"
DATASET_ID="raw_ext"
BUCKET_NAME="intelia-hackathon-dev-raw-data"

TABLES=("customers" "order_items" "orders" "products")

echo "=== BigQuery External Table Setup ==="
echo "Project : $PROJECT_ID"
echo "Dataset : $DATASET_ID"
echo "Bucket  : gs://$BUCKET_NAME"
echo ""

# ── Step 1: Create Tables ───────────────────────────────────────────────────
for TABLE in "${TABLES[@]}"; do
    echo "Creating external table: $TABLE ..."
    
    # Create temporary definition file
    cat <<EOF > /tmp/${TABLE}_def.json
{
  "sourceFormat": "CSV",
  "sourceUris": ["gs://$BUCKET_NAME/$TABLE.csv"],
  "autodetect": true,
  "csvOptions": {
    "skipLeadingRows": 1
  }
}
EOF

    # Create the external table
    bq mk --project_id "$PROJECT_ID" \
        --external_table_definition="/tmp/${TABLE}_def.json" \
        "$DATASET_ID.$TABLE"
        
    echo "  Table $TABLE created."
    rm /tmp/${TABLE}_def.json
done

echo ""
echo "--- Verification ---"
bq ls --project_id "$PROJECT_ID" "$DATASET_ID"

echo ""
echo "=== External table setup complete ==="
