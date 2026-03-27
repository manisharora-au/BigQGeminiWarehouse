# ==============================================================================
# Module: Cloud Monitoring and Alerting
# Description: Log-based metrics and alert policies for pipeline monitoring
# ==============================================================================

variable "project_id" {
  type        = string
  description = "The GCP Project ID"
}

variable "name_prefix" {
  type        = string
  description = "Naming prefix for all resources (org-project-env)"
}

variable "escalation_alerts_topic" {
  type        = string
  description = "Pub/Sub topic for escalation alerts"
}

variable "notification_email" {
  type        = string
  description = "Email address for alert notifications"
  default     = ""
}

variable "labels" {
  type        = map(string)
  description = "Labels to apply to all resources"
  default     = {}
}