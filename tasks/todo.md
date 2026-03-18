# Phase 1: Project Setup & Infrastructure as Code - ToDo

## Task 1: Update API Enablement Script (`scripts/gcp-setup.sh`)
- [x] Review and modify the list of APIs to match our new 3-layer architecture.
    - Add: `storage.googleapis.com` (GCS), `eventarc.googleapis.com` (Eventarc), `dataplex.googleapis.com` (Dataplex for Governance).
    - Retain: `run.googleapis.com` (Cloud Run), `aiplatform.googleapis.com` (Vertex AI), `bigquery.googleapis.com` (BigQuery), etc.
    - Remove: Unused APIs from the previous architecture (e.g., `firestore.googleapis.com`, `routeoptimization.googleapis.com`, `maps-backend.googleapis.com`, `redis.googleapis.com`).

## Task 2: Create Service Account Script (`scripts/setup-service-account.sh`)
- [x] Update the script to leave the existing `route-optimizer-agent` SA untouched (used for another gig).
- [x] Use the new SA name: `hackathon-agent-sa`.
- [x] Apply the **Principle of Least Privilege** by assigning only the roles needed for BigQuery, GCS, Cloud Run, Eventarc, and Vertex AI.
    - `roles/storage.objectViewer` or `roles/storage.objectAdmin` on the raw GCS bucket.
    - `roles/bigquery.dataEditor` and `roles/bigquery.jobUser` for executing dbt models.
    - `roles/run.invoker` for Cloud Run execution.
    - `roles/eventarc.eventReceiver` for Eventarc triggers.
    - `roles/aiplatform.user` for Vertex AI/Gemini integration.
    - `roles/logging.logWriter` for Cloud Logging.

## Task 3: Execute Setup Scripts
- [x] Run the modified `gcp-setup.sh` to enable required GCP APIs for the project.
- [x] Run the modified `setup-service-account.sh` to create the new Service Account and generate the key file.

## Task 4: Bootstrap Terraform Configuration
- [x] Create `terraform/providers.tf` to configure the Google provider using the newly created Service Account credentials (or ADC).
- [x] Create `terraform/variables.tf` to define project variables (e.g., project ID, region, raw bucket name).
- [x] Create `terraform/main.tf` to provision the foundational infrastructure:
    - Raw GCS bucket (`gs://intelia-hackathon-files-raw`).
    - BigQuery Datasets: `raw_ext`, `curated`, `consumption_marts`.
