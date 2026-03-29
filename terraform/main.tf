# ==============================================================================
# Main Terraform Configuration - BigQuery Gemini Data Warehouse
# Description: The entry point orchestrating modular infrastructure for an 
#              event-driven medallion architecture data warehouse.
#              This file maps variables to module inputs and oversees the 
#              dependencies to ensure proper resource creation order.
# ==============================================================================

# Local values for consistent naming conventions and standardized labels
locals {
  # Standardized prefix used to identify resources related to this deployment
  name_prefix = "${var.organization_prefix}-${var.project_name}-${var.environment}"
  # This will equate to intelia-hackathon-dev

  # Base labels attached to all capable Google Cloud resources
  # Common Labels are the labels that will be attached to all the resources
  common_labels = merge(var.labels, {
    environment = var.environment
    project     = var.project_name
    managed_by  = "terraform"
  })
}

# Module 1: APIs Management
# Ensures all necessary Google Cloud APIs required by the architecture are enabled.
module "apis" {
  source = "./modules/apis"

  project_id = var.project_id
  labels     = local.common_labels
  # labels would look like {environment = "dev", project = "hackathon", managed_by = "terraform"}, all applied to this resource at once
}

# Module 2: Cloud Storage - Data Lake Buckets
# Provisions the foundational Cloud Storage buckets serving as the raw data lake.
module "storage" {
  source = "./modules/storage"
  # Each of those lines — project_id = var.project_id, region = var.region — is an explicit handoff. 
  # The root level reads the value from terraform.tfvars via its own variables.tf, 
  # and then manually passes it into the module. The module's own variables.tf declares that it expects a project_id input. 
  # Without that explicit passing, the module has no idea what project_id is.

  project_id    = var.project_id
  region        = var.region
  name_prefix   = local.name_prefix
  labels        = local.common_labels
  force_destroy = var.force_destroy_buckets
  # The value true travels through four files, changing its name once along the way — from force_destroy_buckets 
  # The flow is as under:
  # terraform.tfvars
  #   force_destroy_buckets = true
  #           ↓
  # root variables.tf
  #   variable "force_destroy_buckets"    ← receives "true"
  #           ↓
  # root main.tf
  #   force_destroy = var.force_destroy_buckets    ← reads "true", passes it as "force_destroy"
  #           ↓
  # modules/storage/variables.tf
  #   variable "force_destroy"    ← receives "true" under the new name
  #           ↓
  # modules/storage/main.tf
  #   force_destroy = var.force_destroy    ← resolves to "true"
  #           ↓
  # GCP
  #   The bucket is created with force_destroy = true

  # The value true travels through four files, changing its name once along the way — from force_destroy_buckets 
  # at the root level to force_destroy inside the module — but the underlying value never changes. 
  # By the time it reaches the google_storage_bucket resource, 
  # Terraform substitutes var.force_destroy with the literal value true and sends that instruction to GCP

  depends_on = [module.apis]
}

# Module 3: BigQuery Datasets and Tables
# Creates the curated datasets and structured tables mapping to the medallion architecture.
module "bigquery" {
  source = "./modules/bigquery"

  project_id  = var.project_id
  region      = var.region
  name_prefix = local.name_prefix
  labels      = local.common_labels

  depends_on = [module.apis]
}

# Module 4: IAM Service Accounts and Role Bindings
# Secures access by creating dedicated service accounts with least privilege roles.
module "iam" {
  source = "./modules/iam"

  project_id  = var.project_id
  name_prefix = local.name_prefix
  labels      = local.common_labels

  depends_on = [module.apis]
}

# Module 5: Networking and Pub/Sub
# Sets up asynchronous event notification topics and data pipeline coordination topics.
module "networking" {
  source = "./modules/networking"

  project_id    = var.project_id
  name_prefix   = local.name_prefix
  labels        = local.common_labels
  enable_vpc_sc = var.enable_vpc_service_controls

  depends_on = [module.apis]
}

# Module 6: Dataplex Data Lake and Governance
# Attaches Cloud Storage data lake buckets and BigQuery datasets to Dataplex for governance.
module "dataplex" {
  source = "./modules/dataplex"

  project_id           = var.project_id
  region               = var.region
  name_prefix          = local.name_prefix
  raw_data_bucket_name = module.storage.raw_data_bucket_name
  labels               = local.common_labels

  depends_on = [module.apis, module.storage, module.bigquery]
}

# Module 7: Cloud Monitoring and Alerting
# Creates alert policies and dashboards for tracking data pipeline health and anomalies.
module "monitoring" {
  source = "./modules/monitoring"

  project_id              = var.project_id
  name_prefix             = local.name_prefix
  escalation_alerts_topic = module.networking.escalation_alerts_topic
  notification_email      = var.notification_email
  labels                  = local.common_labels

  depends_on = [module.apis, module.networking]
}
