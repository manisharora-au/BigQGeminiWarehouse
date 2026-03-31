# ==============================================================================
# Module: Networking and VPC Service Controls
# Description: VPC Service Controls perimeter for data security
# VPC Service Controls create a logical perimeter around a set of GCP services in a project. 
# It defines a security perimeter around Google Cloud resources to prevent data exfiltration.  
# The perimeter says: these APIs can only be called from within this defined boundary. 
# Any call originating from outside the perimeter — even with valid credentials — is denied.
# ==============================================================================

# VPC Service Controls perimeter (optional - requires organization access)
# the google_access_context_manager_service_perimeter resource is used to create a VPC Service Controls perimeter.
# A resource block tells Terraform to go and create something in GCP — a bucket, a dataset, a service account.

# VPC Service Controls perimeter (requires organization-level access)
# Commented out until organization access is available
# resource "google_access_context_manager_service_perimeter" "data_perimeter" {
#   count = var.enable_vpc_sc ? 1 : 0
#
#   #  The prupose of parent is to specify the access policy that the perimeter belongs to. 
#   #  The purpose of name is to specify the name of the perimeter. 
#   #  The purpose of title is to specify the title of the perimeter. 
#   parent = "accessPolicies/${data.google_access_context_manager_access_policy.default[0].name}"
#   name   = "accessPolicies/${data.google_access_context_manager_access_policy.default[0].name}/servicePerimeters/${var.name_prefix}-data-perimeter"
#   #  The name will begin to look like accessPolicies/123456789/servicePerimeters/data_perimeter
#   title = "${var.name_prefix} Data Perimeter"
#
#   # Effectively, the below services are now inside a private network and can only be accessed from within that network. 
#   # This is the perimeter
#   status {
#     restricted_services = [
#       "bigquery.googleapis.com",
#       "storage.googleapis.com",
#       "aiplatform.googleapis.com"
#     ]
#
#     resources = [
#       "projects/${var.project_id}"
#     ]
#   }
# }

# A data block is the opposite. It does not create anything. It just goes and reads something that already exists in GCP 
# Get the organization's access policy (if VPC SC is enabled)
# The google_access_context_manager_access_policy resource is used to get the access policy of the organization.
# and brings back information about it.
# VPC Service Controls in GCP live inside something called an Access Policy. 
# Every GCP organisation has exactly one of these — GCP creates it automatically. Terraform did not create it. It already exists.
# Later in the code, when Terraform wants to set up VPC Service Controls, it needs to know the ID of that Access Policy. 
# The data block is how it goes and fetches that ID.
# NOTE: This data source requires organization-level access and may not work in all environments
# data "google_access_context_manager_access_policy" "default" {
#   count = var.enable_vpc_sc ? 1 : 0
#   parent = "organizations/${data.google_project.current.org_id}"
# }

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
