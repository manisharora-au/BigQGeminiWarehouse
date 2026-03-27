# ==============================================================================
# Module: Cloud Monitoring and Alerting
# Description: Log-based metrics and alert policies for pipeline monitoring
# ==============================================================================

# Log-based metric: Cloud Run validator errors
resource "google_logging_metric" "validator_errors" {
  name   = "${var.name_prefix}_validator_errors"
  filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.name_prefix}-validator\" AND severity=\"ERROR\""
  
  metric_descriptor {
    metric_kind = "GAUGE"
    value_type  = "INT64"
    display_name = "Validator Error Count"
  }
  
  value_extractor = "EXTRACT(jsonPayload.error_count)"
  
  label_extractors = {
    "entity_type" = "EXTRACT(jsonPayload.entity_type)"
    "error_type"  = "EXTRACT(jsonPayload.error_type)"
  }
}

# Log-based metric: Pipeline failures
resource "google_logging_metric" "pipeline_failures" {
  name   = "${var.name_prefix}_pipeline_failures"
  filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.name_prefix}-orchestrator\" AND severity=\"ERROR\""
  
  metric_descriptor {
    metric_kind = "GAUGE"
    value_type  = "INT64"
    display_name = "Pipeline Failure Count"
  }
  
  value_extractor = "EXTRACT(jsonPayload.failure_count)"
  
  label_extractors = {
    "pipeline_name" = "EXTRACT(jsonPayload.pipeline_name)"
    "failure_reason" = "EXTRACT(jsonPayload.failure_reason)"
  }
}

# Notification channel: Pub/Sub
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

# Alert policy: Validator errors
resource "google_monitoring_alert_policy" "validator_error_alert" {
  display_name = "${var.name_prefix} Validator Errors"
  combiner     = "OR"
  
  conditions {
    display_name = "Validator error rate"
    
    condition_threshold {
      filter         = "metric.type=\"logging.googleapis.com/user/${var.name_prefix}_validator_errors\" AND resource.type=\"global\""
      duration       = "300s"
      comparison     = "COMPARISON_GREATER_THAN"
      threshold_value = 0
      
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
  
  notification_channels = concat(
    [google_monitoring_notification_channel.pubsub_alerts.id],
    var.notification_email != "" ? [google_monitoring_notification_channel.email_alerts[0].id] : []
  )
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Alert policy: Pipeline failures
resource "google_monitoring_alert_policy" "pipeline_failure_alert" {
  display_name = "${var.name_prefix} Pipeline Failures"
  combiner     = "OR"
  
  conditions {
    display_name = "Pipeline failure rate"
    
    condition_threshold {
      filter         = "metric.type=\"logging.googleapis.com/user/${var.name_prefix}_pipeline_failures\" AND resource.type=\"global\""
      duration       = "300s"
      comparison     = "COMPARISON_GREATER_THAN"
      threshold_value = 0
      
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }
  
  notification_channels = concat(
    [google_monitoring_notification_channel.pubsub_alerts.id],
    var.notification_email != "" ? [google_monitoring_notification_channel.email_alerts[0].id] : []
  )
  
  alert_strategy {
    auto_close = "1800s"
  }
}

# Dashboard: Pipeline Health
resource "google_monitoring_dashboard" "pipeline_health" {
  dashboard_json = jsonencode({
    displayName = "${var.name_prefix} Pipeline Health"
    
    mosaicLayout = {
      tiles = [
        {
          width = 6
          height = 4
          widget = {
            title = "Validator Errors"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"logging.googleapis.com/user/${var.name_prefix}_validator_errors\""
                  aggregation = {
                    alignmentPeriod = "300s"
                    perSeriesAligner = "ALIGN_SUM"
                  }
                }
              }
              sparkChartView = {
                sparkChartType = "SPARK_BAR"
              }
            }
          }
        },
        {
          width = 6
          height = 4
          widget = {
            title = "Pipeline Failures"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"logging.googleapis.com/user/${var.name_prefix}_pipeline_failures\""
                  aggregation = {
                    alignmentPeriod = "300s"
                    perSeriesAligner = "ALIGN_SUM"
                  }
                }
              }
              sparkChartView = {
                sparkChartType = "SPARK_BAR"
              }
            }
          }
        }
      ]
    }
  })
}