# ==============================================================================
# Terraform Variables - BigQuery Gemini Data Warehouse
# Description: All configurable parameters for modular infrastructure
# ==============================================================================

# Core project configuration
variable "project_id" {
  type        = string
  description = "The GCP Project ID where resources will be deployed"
}

variable "region" {
  type        = string
  description = "The GCP region for regional resources (e.g., us-central1, europe-west1)"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)"
}

variable "project_name" {
  type        = string
  description = "Name of the project/application (used in resource naming)"
}

variable "organization_prefix" {
  type        = string
  description = "Organization prefix for resource naming (e.g., 'acme', 'mycompany')"
}

# Optional configuration
variable "labels" {
  type        = map(string)
  description = "Additional labels to apply to all resources"
  default     = {}
}

variable "force_destroy_buckets" {
  type        = bool
  description = "Allow deletion of GCS buckets with objects (use with caution in production)"
  default     = false
}

variable "enable_vpc_service_controls" {
  type        = bool
  description = "Enable VPC Service Controls perimeter (requires organization-level permissions)"
  default     = false
}

variable "notification_email" {
  type        = string
  description = "Email address for monitoring alert notifications (optional)"
  default     = ""
}
