# ==============================================================================
# Module: Dataplex Data Lake and Governance
# Description: Dataplex lake with three zones for medallion architecture
# ==============================================================================

# Dataplex Lake
resource "google_dataplex_lake" "retail_lake" {
  name         = "${var.name_prefix}-retail-lake"
  location     = var.region
  project      = var.project_id
  display_name = "${var.name_prefix} Retail Data Lake"
  description  = "Data lake for retail analytics with medallion architecture"
  
  labels = var.labels
}

# Zone 1: Raw Zone (GCS assets)
resource "google_dataplex_zone" "raw_zone" {
  name         = "raw-zone"
  location     = var.region
  lake         = google_dataplex_lake.retail_lake.name
  project      = var.project_id
  display_name = "Raw Data Zone"
  description  = "Raw data files in Cloud Storage"
  
  type = "RAW"
  
  resource_spec {
    location_type = "SINGLE_REGION"
  }
  
  discovery_spec {
    enabled = true
  }
  
  labels = var.labels
}

# Zone 2: Curated Zone (BigQuery assets)
resource "google_dataplex_zone" "curated_zone" {
  name         = "curated-zone"
  location     = var.region
  lake         = google_dataplex_lake.retail_lake.name
  project      = var.project_id
  display_name = "Curated Data Zone"
  description  = "Curated tables in BigQuery"
  
  type = "CURATED"
  
  resource_spec {
    location_type = "SINGLE_REGION"
  }
  
  discovery_spec {
    enabled = true
  }
  
  labels = var.labels
}

# Zone 3: Consumption Zone (BigQuery marts)
resource "google_dataplex_zone" "consumption_zone" {
  name         = "consumption-zone"
  location     = var.region
  lake         = google_dataplex_lake.retail_lake.name
  project      = var.project_id
  display_name = "Consumption Data Zone"
  description  = "Data marts and dimensional models in BigQuery"
  
  type = "CURATED"
  
  resource_spec {
    location_type = "SINGLE_REGION"
  }
  
  discovery_spec {
    enabled = true
  }
  
  labels = var.labels
}

# Asset: Raw data bucket
resource "google_dataplex_asset" "raw_data_asset" {
  name         = "raw-data-bucket"
  location     = var.region
  lake         = google_dataplex_lake.retail_lake.name
  dataplex_zone = google_dataplex_zone.raw_zone.name
  project      = var.project_id
  display_name = "Raw Data Bucket"
  description  = "Cloud Storage bucket containing raw CSV files"
  
  resource_spec {
    name = "projects/${var.project_id}/buckets/${var.raw_data_bucket_name}"
    type = "STORAGE_BUCKET"
  }
  
  discovery_spec {
    enabled = true
  }
  
  labels = var.labels
}

# Asset: Curated BigQuery dataset
resource "google_dataplex_asset" "curated_dataset_asset" {
  name         = "curated-dataset"
  location     = var.region
  lake         = google_dataplex_lake.retail_lake.name
  dataplex_zone = google_dataplex_zone.curated_zone.name
  project      = var.project_id
  display_name = "Curated Dataset"
  description  = "BigQuery dataset with curated tables"
  
  resource_spec {
    name = "projects/${var.project_id}/datasets/curated"
    type = "BIGQUERY_DATASET"
  }
  
  discovery_spec {
    enabled = true
  }
  
  labels = var.labels
}

# Asset: Marts BigQuery dataset
resource "google_dataplex_asset" "marts_dataset_asset" {
  name         = "marts-dataset"
  location     = var.region
  lake         = google_dataplex_lake.retail_lake.name
  dataplex_zone = google_dataplex_zone.consumption_zone.name
  project      = var.project_id
  display_name = "Data Marts Dataset"
  description  = "BigQuery dataset with dimensional models and data marts"
  
  resource_spec {
    name = "projects/${var.project_id}/datasets/marts"
    type = "BIGQUERY_DATASET"
  }
  
  discovery_spec {
    enabled = true
  }
  
  labels = var.labels
}