# ==============================================================================
# Module: BigQuery Datasets and Tables
# Description: Four datasets for medallion architecture + governance tables
# ==============================================================================

variable "project_id" {
  type        = string
  description = "The GCP Project ID"
}

variable "region" {
  type        = string
  description = "GCP region for BigQuery datasets"
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