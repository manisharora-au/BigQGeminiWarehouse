# ==============================================================================
# Module: APIs Management
# Description: Enables required GCP APIs for data warehouse platform
# ==============================================================================
# The google_project_service resource is used to enable APIs on a GCP project.

resource "google_project_service" "required_apis" {
  for_each = toset(var.required_apis)
  # for_each will begin to look like 
  # google_project_service.required_apis["storage.googleapis.com"] {
  #   project = var.project_id
  #   service = "storage.googleapis.com"
  # }
  # google_project_service.required_apis["bigquery.googleapis.com"] {
  #   project = var.project_id
  #   service = "bigquery.googleapis.com"
  # }
  # and so on for all the APIs in the list

  project = var.project_id
  service = each.value
  # The construct service is used for enabling the APIs on the project.
  # It looks like "storage.googleapis.com", "bigquery.googleapis.com", etc.  

  disable_dependent_services = false
  disable_on_destroy         = false
  # The timeout block is used for setting the time limit for the create and read operations.
  # If the create or read operation takes longer than the specified time, it will be terminated.
  timeouts {
    create = "10m"
    read   = "10m"
  }
}

# resource time_sleep is used to create a delay between the creation of resources.
# In this case, it is used to create a delay between the creation of APIs.
# The delay is set to 30 seconds, and is introduced between each API creation.
# This is done to prevent the APIs from being created too quickly, which could cause errors.
# The depends_on argument is used to specify the resources that the time_sleep resource depends on.
# In this case, it depends on the google_project_service.required_apis resource.

resource "time_sleep" "api_propagation" {
  depends_on = [google_project_service.required_apis]

  create_duration = "30s"
}
