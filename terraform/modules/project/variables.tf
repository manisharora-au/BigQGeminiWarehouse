# ==============================================================================
# Module: Project API Management
# Description: Enables required GCP APIs for data warehouse platform
# ==============================================================================

variable "project_id" {
  type        = string
  description = "The GCP Project ID where APIs will be enabled"
}

variable "required_apis" {
  type = list(string)
  description = "List of GCP APIs to enable"
  default = [
    "storage.googleapis.com",                  # Cloud Storage
    "bigquery.googleapis.com",                 # BigQuery 
    "run.googleapis.com",                      # Cloud Run
    "cloudfunctions.googleapis.com",           # Cloud Functions
    "eventarc.googleapis.com",                 # Eventarc
    "pubsub.googleapis.com",                   # Pub/Sub
    "dataform.googleapis.com",                 # Dataform
    "aiplatform.googleapis.com",               # Vertex AI
    "dataplex.googleapis.com",                 # Dataplex
    "monitoring.googleapis.com",               # Cloud Monitoring
    "logging.googleapis.com",                  # Cloud Logging
    "secretmanager.googleapis.com",            # Secret Manager
    "cloudbuild.googleapis.com",               # Cloud Build
    "iam.googleapis.com",                      # IAM
    "cloudresourcemanager.googleapis.com"      # Resource Manager
  ]
}

variable "labels" {
  type        = map(string)
  description = "Labels to apply to resources"
  default     = {}
}