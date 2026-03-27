# ==============================================================================
# Main Terraform Configuration - BigQuery Gemini Data Warehouse
# Description: Modular infrastructure for event-driven medallion architecture
# ==============================================================================

# Local values for consistent naming and configuration
locals {
  name_prefix = "${var.organization_prefix}-${var.project_name}-${var.environment}"
  
  common_labels = merge(var.labels, {
    environment = var.environment
    project     = var.project_name
    managed_by  = "terraform"
  })
}

# Module 1: Project API Management
module "project" {
  source = "./modules/project"
  
  project_id = var.project_id
  labels     = local.common_labels
}

# Module 2: Cloud Storage - Data Lake Buckets
module "storage" {
  source = "./modules/storage"
  
  project_id    = var.project_id
  region        = var.region
  name_prefix   = local.name_prefix
  labels        = local.common_labels
  force_destroy = var.force_destroy_buckets
  
  depends_on = [module.project]
}

# Module 3: BigQuery Datasets and Tables
module "bigquery" {
  source = "./modules/bigquery"
  
  project_id  = var.project_id
  region      = var.region
  name_prefix = local.name_prefix
  labels      = local.common_labels
  
  depends_on = [module.project]
}

# Module 4: IAM Service Accounts and Role Bindings
module "iam" {
  source = "./modules/iam"
  
  project_id  = var.project_id
  name_prefix = local.name_prefix
  labels      = local.common_labels
  
  depends_on = [module.project]
}

# Module 5: Networking and Pub/Sub
module "networking" {
  source = "./modules/networking"
  
  project_id    = var.project_id
  name_prefix   = local.name_prefix
  labels        = local.common_labels
  enable_vpc_sc = var.enable_vpc_service_controls
  
  depends_on = [module.project]
}

# Module 6: Dataplex Data Lake and Governance
module "dataplex" {
  source = "./modules/dataplex"
  
  project_id             = var.project_id
  region                 = var.region
  name_prefix            = local.name_prefix
  raw_data_bucket_name   = module.storage.raw_data_bucket_name
  labels                 = local.common_labels
  
  depends_on = [module.project, module.storage, module.bigquery]
}

# Module 7: Cloud Monitoring and Alerting
module "monitoring" {
  source = "./modules/monitoring"
  
  project_id              = var.project_id
  name_prefix             = local.name_prefix
  escalation_alerts_topic = module.networking.escalation_alerts_topic
  notification_email      = var.notification_email
  labels                  = local.common_labels
  
  depends_on = [module.project, module.networking]
}