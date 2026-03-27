# ==============================================================================
# Module: IAM Outputs
# ==============================================================================

output "cloudfunction_router_email" {
  description = "Email of Cloud Function router service account"
  value       = google_service_account.cloudfunction_router.email
}

output "cloudrun_validator_email" {
  description = "Email of Cloud Run validator service account"
  value       = google_service_account.cloudrun_validator.email
}

output "cloudrun_orchestrator_email" {
  description = "Email of Cloud Run orchestrator service account"
  value       = google_service_account.cloudrun_orchestrator.email
}

output "dataform_email" {
  description = "Email of Dataform service account"
  value       = google_service_account.dataform.email
}

output "vertexai_email" {
  description = "Email of Vertex AI service account"
  value       = google_service_account.vertexai.email
}

output "looker_email" {
  description = "Email of Looker Studio service account"
  value       = google_service_account.looker.email
}

output "cloudbuild_email" {
  description = "Email of Cloud Build service account"
  value       = google_service_account.cloudbuild.email
}

output "all_service_accounts" {
  description = "Map of all service account emails"
  value = {
    cloudfunction_router   = google_service_account.cloudfunction_router.email
    cloudrun_validator     = google_service_account.cloudrun_validator.email
    cloudrun_orchestrator  = google_service_account.cloudrun_orchestrator.email
    dataform              = google_service_account.dataform.email
    vertexai              = google_service_account.vertexai.email
    looker                = google_service_account.looker.email
    cloudbuild            = google_service_account.cloudbuild.email
  }
}