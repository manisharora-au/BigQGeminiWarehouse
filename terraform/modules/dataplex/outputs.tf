# ==============================================================================
# Module: Dataplex Outputs
# ==============================================================================

output "lake_name" {
  description = "Name of the Dataplex lake"
  value       = google_dataplex_lake.retail_lake.name
}

output "raw_zone_name" {
  description = "Name of the raw data zone"
  value       = google_dataplex_zone.raw_zone.name
}

output "curated_zone_name" {
  description = "Name of the curated data zone"
  value       = google_dataplex_zone.curated_zone.name
}

output "consumption_zone_name" {
  description = "Name of the consumption data zone"
  value       = google_dataplex_zone.consumption_zone.name
}

output "all_assets" {
  description = "List of all Dataplex assets"
  value = [
    google_dataplex_asset.raw_data_asset.name,
    google_dataplex_asset.curated_dataset_asset.name,
    google_dataplex_asset.marts_dataset_asset.name
  ]
}