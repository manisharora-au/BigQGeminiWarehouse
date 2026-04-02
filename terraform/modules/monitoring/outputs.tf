# ==============================================================================
# Module: Monitoring Outputs (Simplified)
# ==============================================================================

output "log_metrics" {
  description = "List of created log-based metrics"
  value = []
}

output "alert_policies" {
  description = "List of alert policy IDs"
  value = []
}

output "notification_channels" {
  description = "Map of notification channel IDs"
  value = {
    pubsub = google_monitoring_notification_channel.pubsub_alerts.id
    email  = var.notification_email != "" ? google_monitoring_notification_channel.email_alerts[0].id : null
  }
}

output "dashboard_url" {
  description = "URL of the pipeline health dashboard"
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.pipeline_health.id}"
}