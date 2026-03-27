# ==============================================================================
# Module: Project API Management
# Description: Enables required GCP APIs for data warehouse platform
# ==============================================================================

resource "google_project_service" "required_apis" {
  for_each = toset(var.required_apis)
  
  project = var.project_id
  service = each.value
  
  disable_dependent_services = false
  disable_on_destroy         = false
  
  timeouts {
    create = "10m"
    read   = "10m"
  }
}

resource "time_sleep" "api_propagation" {
  depends_on = [google_project_service.required_apis]
  
  create_duration = "30s"
}