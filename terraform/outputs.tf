# ------------------------------------------------------------------------------
# Output values for use by other systems
# ------------------------------------------------------------------------------

output "project_id" {
  description = "The GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "The GCP region where resources are deployed"
  value       = var.region
}

output "raw_bucket_name" {
  description = "Name of the GCS bucket for raw data"
  value       = google_storage_bucket.raw_data.name
}

output "raw_bucket_url" {
  description = "GCS URL of the raw data bucket"
  value       = google_storage_bucket.raw_data.url
}

output "raw_dataset_id" {
  description = "BigQuery dataset ID for raw external tables"
  value       = google_bigquery_dataset.raw_ext.dataset_id
}

output "curated_dataset_id" {
  description = "BigQuery dataset ID for curated data"
  value       = google_bigquery_dataset.curated.dataset_id
}

output "consumption_dataset_id" {
  description = "BigQuery dataset ID for consumption data marts"
  value       = google_bigquery_dataset.consumption_marts.dataset_id
}

output "dataset_locations" {
  description = "Map of dataset names to their locations"
  value = {
    raw_ext            = google_bigquery_dataset.raw_ext.location
    curated           = google_bigquery_dataset.curated.location
    consumption_marts = google_bigquery_dataset.consumption_marts.location
  }
}

output "resource_labels" {
  description = "Common labels applied to all resources"
  value       = local.common_labels
}

output "name_prefix" {
  description = "The generated naming prefix used for resources"
  value       = local.name_prefix
}

# Service account outputs
output "service_account_email" {
  description = "Email of the created service account"
  value       = google_service_account.agent.email
}

output "service_account_name" {
  description = "Name of the created service account"
  value       = google_service_account.agent.name
}

output "service_account_key" {
  description = "Private key for the service account (base64 encoded)"
  value       = var.create_service_account_key ? google_service_account_key.agent_key[0].private_key : null
  sensitive   = true
}

output "enabled_apis" {
  description = "List of APIs that were enabled"
  value       = local.required_apis
}