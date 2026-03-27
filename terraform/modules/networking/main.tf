# ==============================================================================
# Module: Networking and VPC Service Controls
# Description: VPC Service Controls perimeter for data security
# ==============================================================================

# VPC Service Controls perimeter (optional - requires organization access)
resource "google_access_context_manager_service_perimeter" "data_perimeter" {
  count  = var.enable_vpc_sc ? 1 : 0
  
  parent = "accessPolicies/${data.google_access_context_manager_access_policy.default[0].name}"
  name   = "accessPolicies/${data.google_access_context_manager_access_policy.default[0].name}/servicePerimeters/${var.name_prefix}-data-perimeter"
  title  = "${var.name_prefix} Data Perimeter"
  
  status {
    restricted_services = [
      "bigquery.googleapis.com",
      "storage.googleapis.com",
      "aiplatform.googleapis.com"
    ]
    
    resources = [
      "projects/${var.project_id}"
    ]
  }
}

# Get the organization's access policy (if VPC SC is enabled)
data "google_access_context_manager_access_policy" "default" {
  count  = var.enable_vpc_sc ? 1 : 0
  
  parent = "organizations/${data.google_project.current.org_id}"
}

# Get current project information
data "google_project" "current" {
  project_id = var.project_id
}

# Pub/Sub topic for pipeline coordination
resource "google_pubsub_topic" "pipeline_coordinator_trigger" {
  name = "${var.name_prefix}-pipeline-coordinator-trigger"
  
  labels = merge(var.labels, {
    purpose = "pipeline-coordination"
  })
}

# Pub/Sub topic for escalation alerts
resource "google_pubsub_topic" "escalation_alerts" {
  name = "${var.name_prefix}-escalation-alerts"
  
  labels = merge(var.labels, {
    purpose = "alerting"
  })
}