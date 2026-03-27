# ==============================================================================
# Module: BigQuery Outputs
# ==============================================================================

output "validated_external_dataset_id" {
  description = "ID of the validated external dataset"
  value       = google_bigquery_dataset.validated_external.dataset_id
}

output "curated_dataset_id" {
  description = "ID of the curated dataset"
  value       = google_bigquery_dataset.curated.dataset_id
}

output "marts_dataset_id" {
  description = "ID of the marts dataset"
  value       = google_bigquery_dataset.marts.dataset_id
}

output "governance_dataset_id" {
  description = "ID of the governance dataset"
  value       = google_bigquery_dataset.governance.dataset_id
}

output "governance_tables" {
  description = "List of governance table IDs"
  value = [
    google_bigquery_table.validation_log.table_id,
    google_bigquery_table.quality_failures.table_id,
    google_bigquery_table.ingestion_log.table_id,
    google_bigquery_table.ai_insights.table_id
  ]
}