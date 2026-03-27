# ==============================================================================
# Module: Networking Outputs
# ==============================================================================

output "pipeline_coordinator_topic" {
  description = "Pub/Sub topic for pipeline coordination"
  value       = google_pubsub_topic.pipeline_coordinator_trigger.name
}

output "escalation_alerts_topic" {
  description = "Pub/Sub topic for escalation alerts"
  value       = google_pubsub_topic.escalation_alerts.name
}

output "vpc_sc_perimeter" {
  description = "VPC Service Controls perimeter (if enabled)"
  value       = var.enable_vpc_sc ? google_access_context_manager_service_perimeter.data_perimeter[0].name : null
}