# ------------------------------------------------------------------------------
# 1. Google Cloud Storage: Raw Layer
# ------------------------------------------------------------------------------
resource "google_storage_bucket" "raw_data" {
  name                        = "${var.raw_bucket_name}-${var.project_id}"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment = var.environment
    layer       = "raw"
  }
}

# ------------------------------------------------------------------------------
# 2. BigQuery Datasets: Raw, Curated, Consumption
# ------------------------------------------------------------------------------
resource "google_bigquery_dataset" "raw_ext" {
  dataset_id                  = "raw_ext"
  friendly_name               = "Raw External Tables"
  description                 = "Dataset for external tables pointing directly to the raw GCS bucket"
  location                    = var.region
  default_table_expiration_ms = null # Tables don't expire
  
  labels = {
    environment = var.environment
    layer       = "raw"
  }
}

resource "google_bigquery_dataset" "curated" {
  dataset_id                  = "curated"
  friendly_name               = "Curated Data"
  description                 = "Dataset for conformed and cleaned tables built by dbt"
  location                    = var.region
  default_table_expiration_ms = null
  
  labels = {
    environment = var.environment
    layer       = "curated"
  }
}

resource "google_bigquery_dataset" "consumption_marts" {
  dataset_id                  = "consumption_marts"
  friendly_name               = "Consumption Data Marts"
  description                 = "Dataset for dimensional models and data marts used by Looker/GenAI"
  location                    = var.region
  default_table_expiration_ms = null
  
  labels = {
    environment = var.environment
    layer       = "consumption"
  }
}
