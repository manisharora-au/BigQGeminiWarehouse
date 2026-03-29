# ==============================================================================
# Terraform Variables - BigQuery Gemini Data Warehouse
# Description: Defines all configurable input parameters for the modular 
#              infrastructure deployment. Includes required core configuration 
#              and optional operational toggles.
# ==============================================================================

# Core project configuration
# These variables must be provided for a successful deployment.
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
  description = "Environment name indicating the deployment stage (e.g., dev, staging, prod)"
}

variable "project_name" {
  type        = string
  description = "Name of the project/application to be used as a base in resource naming"
}

variable "organization_prefix" {
  type        = string
  description = "Organization prefix used to create globally unique resource names (e.g., 'acme', 'mycompany')"
}

# Optional configuration
# These variables provide defaults, enabling customization for monitoring,
# labeling, and advanced security configurations.
variable "labels" {
  type        = map(string)
  description = "Additional key-value labels to consistently tag all created resources"
  default     = {}
}

variable "force_destroy_buckets" {
  type        = bool
  description = "Allow deletion of GCS data lake buckets even if they contain objects (CAUTION: Use false for production)"
  default     = false
}

variable "enable_vpc_service_controls" {
  type        = bool
  description = "Enable Google Cloud VPC Service Controls perimeter (requires org-level IAM permissions)"
  default     = false
}

variable "notification_email" {
  type        = string
  description = "Email address for receiving Cloud Monitoring alert notifications (optional)"
  default     = ""
}
