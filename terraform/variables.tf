variable "project_id" {
  type        = string
  description = "The GCP Project ID where resources will be deployed"
  default     = "manish-sandpit"
}

variable "region" {
  type        = string
  description = "The GCP region to deploy resources (e.g., australia-southeast1)"
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "The environment name (e.g., dev, prod)"
  default     = "dev"
}

variable "raw_bucket_name" {
  type        = string
  description = "Name of the GCS bucket for raw data ingestion"
  default     = "intelia-hackathon-files-raw"
}
