# ==============================================================================
# Module: Dataplex Data Lake and Governance
# Description: Dataplex lake with three zones for medallion architecture
# ==============================================================================

variable "project_id" {
  type        = string
  description = "The GCP Project ID"
}

variable "region" {
  type        = string
  description = "GCP region for Dataplex resources"
}

variable "name_prefix" {
  type        = string
  description = "Naming prefix for all resources (org-project-env)"
}

variable "raw_data_bucket_name" {
  type        = string
  description = "Name of the raw data GCS bucket"
}

variable "labels" {
  type        = map(string)
  description = "Labels to apply to all resources"
  default     = {}
}