# ==============================================================================
# Module: Cloud Storage - Data Lake Buckets
# Description: GCS buckets with lifecycle rules and prefixes for medallion architecture
# ==============================================================================

variable "project_id" {
  type        = string
  description = "The GCP Project ID"
}

variable "region" {
  type        = string
  description = "GCP region for resources"
}

variable "name_prefix" {
  type        = string
  description = "Naming prefix for all resources (org-project-env)"
}

variable "labels" {
  type        = map(string)
  description = "Labels to apply to all resources"
  default     = {}
}

variable "force_destroy" {
  type        = bool
  description = "Allow deletion of bucket with objects (use with caution)"
  default     = false
}