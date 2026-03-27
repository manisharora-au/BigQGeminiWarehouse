# ==============================================================================
# Module: IAM Service Accounts and Role Bindings
# Description: Service accounts with least-privilege IAM roles
# ==============================================================================

# Service Account: Cloud Functions File Router
resource "google_service_account" "cloudfunction_router" {
  account_id   = "${var.name_prefix}-cf-router"
  display_name = "Cloud Function File Router"
  description  = "Service account for Cloud Function that routes files from inbox to raw folders"
  project      = var.project_id
}

resource "google_project_iam_member" "cloudfunction_router_roles" {
  for_each = toset([
    "roles/storage.objectAdmin",     # Read from inbox/, write to raw/
    "roles/logging.logWriter"        # Write logs
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloudfunction_router.email}"
}

# Service Account: Cloud Run Validator
resource "google_service_account" "cloudrun_validator" {
  account_id   = "${var.name_prefix}-cr-validator"
  display_name = "Cloud Run Validator"
  description  = "Service account for Cloud Run validator service"
  project      = var.project_id
}

resource "google_project_iam_member" "cloudrun_validator_roles" {
  for_each = toset([
    "roles/storage.objectViewer",    # Read files for validation
    "roles/storage.objectCreator",   # Write to validated/ and quarantine/
    "roles/bigquery.dataEditor",     # Write to governance.validation_log
    "roles/bigquery.jobUser",        # Run BigQuery jobs
    "roles/pubsub.publisher",        # Publish to pipeline-coordinator-trigger
    "roles/logging.logWriter"        # Write logs
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloudrun_validator.email}"
}

# Service Account: Cloud Run Orchestrator (Pipeline Coordinator Agent)
resource "google_service_account" "cloudrun_orchestrator" {
  account_id   = "${var.name_prefix}-cr-orchestrator"
  display_name = "Cloud Run Pipeline Orchestrator"
  description  = "Service account for Google ADK Pipeline Coordinator Agent"
  project      = var.project_id
}

resource "google_project_iam_member" "cloudrun_orchestrator_roles" {
  for_each = toset([
    "roles/bigquery.dataViewer",     # Read governance tables
    "roles/bigquery.dataEditor",     # Write to governance tables
    "roles/bigquery.jobUser",        # Run BigQuery jobs
    "roles/dataform.editor",         # Trigger Dataform workflows
    "roles/storage.objectAdmin",     # Move files for quarantine
    "roles/pubsub.publisher",        # Publish escalation messages
    "roles/logging.logWriter"        # Write logs
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloudrun_orchestrator.email}"
}

# Service Account: Dataform
resource "google_service_account" "dataform" {
  account_id   = "${var.name_prefix}-dataform"
  display_name = "Dataform Service Account"
  description  = "Service account for Dataform transformations"
  project      = var.project_id
}

resource "google_project_iam_member" "dataform_roles" {
  for_each = toset([
    "roles/bigquery.dataEditor",     # Read/write all datasets
    "roles/bigquery.jobUser",        # Run transformation jobs
    "roles/storage.objectViewer",    # Read external table sources
    "roles/logging.logWriter"        # Write logs
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.dataform.email}"
}

# Service Account: Vertex AI (for Conversational Analytics Agent)
resource "google_service_account" "vertexai" {
  account_id   = "${var.name_prefix}-vertexai"
  display_name = "Vertex AI Analytics Agent"
  description  = "Service account for Google ADK Conversational Analytics Agent"
  project      = var.project_id
}

resource "google_project_iam_member" "vertexai_roles" {
  for_each = toset([
    "roles/bigquery.dataViewer",     # Read mart tables for queries
    "roles/bigquery.jobUser",        # Run analytical queries
    "roles/aiplatform.user",         # Access Vertex AI models
    "roles/logging.logWriter"        # Write logs
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.vertexai.email}"
}

# Service Account: Looker Studio (for dashboard access)
resource "google_service_account" "looker" {
  account_id   = "${var.name_prefix}-looker"
  display_name = "Looker Studio Service Account"
  description  = "Service account for Looker Studio dashboard connections"
  project      = var.project_id
}

resource "google_project_iam_member" "looker_roles" {
  for_each = toset([
    "roles/bigquery.dataViewer",     # Read marts and governance datasets
    "roles/bigquery.jobUser"         # Run dashboard queries
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.looker.email}"
}

# Service Account: Cloud Build (for CI/CD pipeline)
resource "google_service_account" "cloudbuild" {
  account_id   = "${var.name_prefix}-cloudbuild"
  display_name = "Cloud Build Service Account"
  description  = "Service account for Cloud Build CI/CD pipeline"
  project      = var.project_id
}

resource "google_project_iam_member" "cloudbuild_roles" {
  for_each = toset([
    "roles/storage.admin",           # Deploy Cloud Functions
    "roles/run.admin",               # Deploy Cloud Run services
    "roles/dataform.admin",          # Deploy Dataform models
    "roles/iam.serviceAccountUser",  # Act as service accounts
    "roles/logging.logWriter"        # Write logs
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.cloudbuild.email}"
}