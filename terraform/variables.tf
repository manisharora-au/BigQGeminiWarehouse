# Required variables - no defaults to force explicit configuration
# variable.tf is simply a contract that tells users what inputs the infrastructure expects, 
# what types they should be, and what they're used for. The
# actual values live separately in terraform.tfvars

variable "project_id" {
  type        = string
  description = "The GCP Project ID where resources will be deployed"
}

variable "region" {
  type        = string
  description = "The GCP region to deploy resources (e.g., us-central1, australia-southeast1)"
}

variable "environment" {
  type        = string
  description = "The environment name (e.g., dev, staging, prod)"
}

# Naming configuration
variable "project_name" {
  type        = string
  description = "Base name for the project used in resource naming"
}

variable "organization_prefix" {
  type        = string
  description = "Organization prefix for resource naming (e.g., company name)"
}

# Optional dataset naming overrides
variable "raw_dataset_name" {
  type        = string
  description = "Name for the raw external dataset"
  default     = "raw_ext"
}

variable "curated_dataset_name" {
  type        = string
  description = "Name for the curated dataset"
  default     = "curated"
}

variable "consumption_dataset_name" {
  type        = string
  description = "Name for the consumption dataset"
  default     = "consumption_marts"
}

# Service account configuration
variable "service_account_name" {
  type        = string
  description = "Name for the service account (without @project.iam.gserviceaccount.com)"
  default     = null
}

variable "service_account_display_name" {
  type        = string
  description = "Display name for the service account"
  default     = null
}

# Resource labeling
variable "labels" {
  type        = map(string)
  description = "Additional labels to apply to all resources"
  default     = {}
}

# Data lifecycle
variable "raw_data_retention_days" {
  type        = number
  description = "Number of days to retain raw data in GCS before deletion"
  default     = 7
}

# Service account key creation
variable "create_service_account_key" {
  type        = bool
  description = "Whether to create a service account key (use with caution in production)"
  default     = false
}
