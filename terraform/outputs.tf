# ==============================================================================
# Terraform Outputs - BigQuery Gemini Data Warehouse
# Description: Output values from all infrastructure modules
# ==============================================================================

# Project outputs
output "project_id" {
  description = "The GCP Project ID"
  value       = var.project_id
}

output "enabled_apis" {
  description = "List of enabled GCP APIs"
  value       = module.project.enabled_apis
}

# Storage outputs
output "raw_data_bucket" {
  description = "Name of the primary data bucket"
  value       = module.storage.raw_data_bucket_name
}

output "functions_source_bucket" {
  description = "Name of the Cloud Functions source bucket"
  value       = module.storage.functions_source_bucket_name
}

output "bucket_prefixes" {
  description = "List of created GCS prefixes"
  value       = module.storage.bucket_prefixes
}

# BigQuery outputs
output "bigquery_datasets" {
  description = "Map of BigQuery dataset IDs"
  value = {
    validated_external = module.bigquery.validated_external_dataset_id
    curated           = module.bigquery.curated_dataset_id
    marts             = module.bigquery.marts_dataset_id
    governance        = module.bigquery.governance_dataset_id
  }
}

output "governance_tables" {
  description = "List of governance table IDs"
  value       = module.bigquery.governance_tables
}

# IAM outputs
output "service_accounts" {
  description = "Map of all service account emails"
  value       = module.iam.all_service_accounts
}

# Networking outputs
output "pubsub_topics" {
  description = "Map of Pub/Sub topic names"
  value = {
    pipeline_coordinator = module.networking.pipeline_coordinator_topic
    escalation_alerts   = module.networking.escalation_alerts_topic
  }
}

# Dataplex outputs
output "dataplex_lake" {
  description = "Name of the Dataplex lake"
  value       = module.dataplex.lake_name
}

output "dataplex_zones" {
  description = "Map of Dataplex zone names"
  value = {
    raw         = module.dataplex.raw_zone_name
    curated     = module.dataplex.curated_zone_name
    consumption = module.dataplex.consumption_zone_name
  }
}

# Monitoring outputs
output "monitoring_dashboard" {
  description = "URL of the pipeline health monitoring dashboard"
  value       = module.monitoring.dashboard_url
}

output "alert_policies" {
  description = "List of monitoring alert policy IDs"
  value       = module.monitoring.alert_policies
}

# Infrastructure summary
output "infrastructure_summary" {
  description = "Summary of deployed infrastructure"
  value = {
    name_prefix           = local.name_prefix
    region               = var.region
    environment          = var.environment
    raw_data_bucket      = module.storage.raw_data_bucket_name
    bigquery_datasets    = length(module.bigquery.governance_tables)
    service_accounts     = length(keys(module.iam.all_service_accounts))
    dataplex_assets      = length(module.dataplex.all_assets)
  }
}