# ==============================================================================
# Module: Project API Management Outputs
# ==============================================================================

output "enabled_apis" {
  description = "List of enabled APIs"
  value       = [for api in google_project_service.required_apis : api.service]
}

output "api_propagation_complete" {
  description = "Marker for API propagation completion"
  value       = time_sleep.api_propagation.id
}