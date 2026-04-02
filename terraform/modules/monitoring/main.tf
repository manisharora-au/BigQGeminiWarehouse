# ==============================================================================
# Module: Cloud Monitoring and Alerting (Very Simple)
# Description: Basic notification channels only - reliable and simple
# ==============================================================================

# Notification channel: Pub/Sub
# Simple notification channel for sending alerts via Pub/Sub
resource "google_monitoring_notification_channel" "pubsub_alerts" {
  display_name = "${var.name_prefix} Pub/Sub Alerts"
  type         = "pubsub"
  
  labels = {
    topic = var.escalation_alerts_topic
  }
}

# Notification channel: Email (if provided)
resource "google_monitoring_notification_channel" "email_alerts" {
  count = var.notification_email != "" ? 1 : 0
  
  display_name = "${var.name_prefix} Email Alerts"
  type         = "email"
  
  labels = {
    email_address = var.notification_email
  }
}

# Simple dashboard with basic monitoring placeholder
resource "google_monitoring_dashboard" "pipeline_health" {
  dashboard_json = jsonencode({
    displayName = "${var.name_prefix} Pipeline Health"
    
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 12
          height = 4
          xPos   = 0
          yPos   = 0
          widget = {
            title = "Monitoring Status"
            text = {
              content = "Basic monitoring is active. Notification channels configured for Pub/Sub and Email alerts."
              format = "MARKDOWN"
            }
          }
        }
      ]
    }
  })
}