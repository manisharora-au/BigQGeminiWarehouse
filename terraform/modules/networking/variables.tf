# ==============================================================================
# Module: Networking and VPC Service Controls
# Description: VPC Service Controls perimeter for data security
# ==============================================================================

variable "project_id" {
  type        = string
  description = "The GCP Project ID"
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

variable "enable_vpc_sc" {
  type        = bool
  description = "Enable VPC Service Controls (requires organization-level permissions)"
  default     = false
}