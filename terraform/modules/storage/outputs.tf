# ==============================================================================
# Module: Cloud Storage Outputs
# ==============================================================================

output "raw_data_bucket_name" {
  description = "Name of the primary data bucket"
  value       = google_storage_bucket.raw_data.name
}

output "raw_data_bucket_url" {
  description = "URL of the primary data bucket"
  value       = google_storage_bucket.raw_data.url
}

output "functions_source_bucket_name" {
  description = "Name of the Cloud Functions source bucket"
  value       = google_storage_bucket.functions_source.name
}

output "bucket_prefixes" {
  description = "List of created bucket prefixes"
  value = [
    google_storage_bucket_object.inbox_prefix.name,
    google_storage_bucket_object.raw_prefix.name,
    google_storage_bucket_object.validated_prefix.name,
    google_storage_bucket_object.quarantine_prefix.name,
    google_storage_bucket_object.archive_prefix.name,
    google_storage_bucket_object.temp_prefix.name
  ]
}