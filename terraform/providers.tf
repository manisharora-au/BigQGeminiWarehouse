# ==============================================================================
# Providers Configuration - BigQuery Gemini Data Warehouse
# Description: Defines the Terraform environment requirements and configures 
#              the underlying infrastructure providers (principally Google Cloud).
# ==============================================================================

# Terraform constraints and provider inclusions
terraform {
  # Mandates a minimum compatible version of the Terraform engine
  required_version = ">= 1.4.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

# Configure the primary Google Cloud provider with the active project and region
provider "google" {
  project = var.project_id
  region  = var.region
}
