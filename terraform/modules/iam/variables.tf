# ==============================================================================
# Module: IAM Service Accounts and Role Bindings
# Description: Service accounts with least-privilege IAM roles
# ==============================================================================

variable "project_id" {
  type        = string
  description = "The GCP Project ID"
}

variable "name_prefix" {
  type        = string
  description = "Naming prefix for all resources (org-project-env)"
}

variable "service_account_prefix" {
  type        = string
  description = "Shortened prefix for service account names (max 30 chars total)"
  default     = null
}

variable "labels" {
  type        = map(string)
  description = "Labels to apply to all resources"
  default     = {}
}