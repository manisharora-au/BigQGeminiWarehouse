# ==============================================================================
# Module: Networking Outputs
# ==============================================================================

output "pipeline_coordinator_topic" {
  description = "Pub/Sub topic for pipeline coordination"
  value       = google_pubsub_topic.pipeline_coordinator_trigger.name
}

output "escalation_alerts_topic" {
  description = "Pub/Sub topic for escalation alerts (full resource path for notification channels)"
  value       = google_pubsub_topic.escalation_alerts.id
}

output "vpc_sc_perimeter" {
  description = "VPC Service Controls perimeter (if enabled)"
  value       = var.enable_vpc_sc ? "vpc-sc-commented-out-pending-org-access" : null
}