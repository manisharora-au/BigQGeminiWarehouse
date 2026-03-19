# ------------------------------------------------------------------------------
# Local values for consistent naming
# ------------------------------------------------------------------------------
locals {
  # Generate consistent naming pattern
  name_prefix = "${var.organization_prefix}-${var.project_name}-${var.environment}"
  
  # Service account naming
  service_account_name = var.service_account_name != null ? var.service_account_name : "${local.name_prefix}-agent-sa"
  service_account_display_name = var.service_account_display_name != null ? var.service_account_display_name : "${title(var.project_name)} Agent SA (${var.environment})"
  
  # Common labels
  common_labels = merge(var.labels, {
    environment = var.environment
    project     = var.project_name
    managed_by  = "terraform"
  })

  # Required APIs for data warehouse
  required_apis = [
    "run.googleapis.com",                      # Cloud Run - orchestration
    "eventarc.googleapis.com",                 # Eventarc - event-driven triggers
    "aiplatform.googleapis.com",               # Vertex AI - GenAI capabilities
    "storage.googleapis.com",                  # Cloud Storage - raw data
    "bigquery.googleapis.com",                 # BigQuery - analytics warehouse
    "dataplex.googleapis.com",                 # Dataplex - data governance
    "logging.googleapis.com",                  # Cloud Logging
    "monitoring.googleapis.com",               # Cloud Monitoring
    "iam.googleapis.com",                      # IAM
    "cloudresourcemanager.googleapis.com",     # Resource management
  ]

  # IAM roles for service account
  service_account_roles = [
    "roles/storage.objectAdmin",              # GCS - read/write raw files
    "roles/bigquery.dataEditor",              # BigQuery - read/write datasets
    "roles/bigquery.jobUser",                 # BigQuery - run jobs/queries
    "roles/run.invoker",                      # Cloud Run - invoke jobs
    "roles/eventarc.eventReceiver",           # Eventarc - receive events
    "roles/aiplatform.user",                  # Vertex AI - GenAI integration
    "roles/logging.logWriter",                # Cloud Logging
  ]
}

# ------------------------------------------------------------------------------
# 0. Enable Required APIs (skipped - APIs already enabled via earlier scripts)
# ------------------------------------------------------------------------------
# resource "google_project_service" "required_apis" {
#   for_each = toset(local.required_apis)
#   
#   project = var.project_id
#   service = each.value
#   
#   disable_dependent_services = false
#   disable_on_destroy         = false
# }

# ------------------------------------------------------------------------------
# 1. Service Account
# ------------------------------------------------------------------------------
resource "google_service_account" "agent" {
  account_id   = local.service_account_name
  display_name = local.service_account_display_name
  description  = "Service account for ${var.project_name} data pipeline (BigQuery, Dataform, Eventarc)"
  project      = var.project_id
  
  # depends_on = [google_project_service.required_apis]
}

resource "google_project_iam_member" "agent_roles" {
  for_each = toset(local.service_account_roles)
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.agent.email}"
  
  depends_on = [google_service_account.agent]
}

# Optional: Generate service account key (use with caution in production)
resource "google_service_account_key" "agent_key" {
  count = var.create_service_account_key ? 1 : 0
  
  service_account_id = google_service_account.agent.name
}

# ------------------------------------------------------------------------------
# 2. Google Cloud Storage: Raw Layer
# ------------------------------------------------------------------------------
resource "google_storage_bucket" "raw_data" {
  name                        = "${local.name_prefix}-raw-data"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = var.raw_data_retention_days
    }
    action {
      type = "Delete"
    }
  }

  labels = merge(local.common_labels, {
    layer = "raw"
  })
}

# ------------------------------------------------------------------------------
# 3. BigQuery Datasets: Raw, Curated, Consumption
# ------------------------------------------------------------------------------
resource "google_bigquery_dataset" "raw_ext" {
  dataset_id                  = var.raw_dataset_name
  friendly_name               = "Raw External Tables (${var.environment})"
  description                 = "Dataset for external tables pointing directly to the raw GCS bucket for ${var.project_name} project"
  location                    = var.region
  default_table_expiration_ms = null # Tables don't expire
  
  labels = merge(local.common_labels, {
    layer = "raw"
  })
}

resource "google_bigquery_dataset" "curated" {
  dataset_id                  = var.curated_dataset_name
  friendly_name               = "Curated Data (${var.environment})"
  description                 = "Dataset for conformed and cleaned tables built by Dataform for ${var.project_name} project"
  location                    = var.region
  default_table_expiration_ms = null
  
  labels = merge(local.common_labels, {
    layer = "curated"
  })
}

resource "google_bigquery_dataset" "consumption_marts" {
  dataset_id                  = var.consumption_dataset_name
  friendly_name               = "Consumption Data Marts (${var.environment})"
  description                 = "Dataset for dimensional models and data marts used by Looker/GenAI for ${var.project_name} project"
  location                    = var.region
  default_table_expiration_ms = null
  
  labels = merge(local.common_labels, {
    layer = "consumption"
  })
}
