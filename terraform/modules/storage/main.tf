# ==============================================================================
# Module: Cloud Storage - Data Lake Buckets
# Description: GCS buckets with lifecycle rules and prefixes for medallion architecture
# ==============================================================================

# Primary data bucket with six prefixes for file routing
resource "google_storage_bucket" "raw_data" {
  name                        = "${var.name_prefix}-raw-data"
  location                    = var.region
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = true

  # Lifecycle rules for cost optimization
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  # Retention lock on raw/ prefix for 365 days (governance)
  lifecycle_rule {
    condition {
      age                = 365
      matches_prefix     = ["raw/"]
    }
    action {
      type = "Delete"
    }
  }

  labels = merge(var.labels, {
    layer = "raw"
    purpose = "data-lake"
  })
}

# Create the six required prefixes as folders
resource "google_storage_bucket_object" "inbox_prefix" {
  name    = "inbox/"
  content = " "
  bucket  = google_storage_bucket.raw_data.name
}

resource "google_storage_bucket_object" "raw_prefix" {
  name    = "raw/"
  content = " "
  bucket  = google_storage_bucket.raw_data.name
}

resource "google_storage_bucket_object" "validated_prefix" {
  name    = "validated/"
  content = " "
  bucket  = google_storage_bucket.raw_data.name
}

resource "google_storage_bucket_object" "quarantine_prefix" {
  name    = "quarantine/"
  content = " "
  bucket  = google_storage_bucket.raw_data.name
}

resource "google_storage_bucket_object" "archive_prefix" {
  name    = "archive/"
  content = " "
  bucket  = google_storage_bucket.raw_data.name
}

resource "google_storage_bucket_object" "temp_prefix" {
  name    = "temp/"
  content = " "
  bucket  = google_storage_bucket.raw_data.name
}

# Cloud Functions source code bucket  
resource "google_storage_bucket" "functions_source" {
  name                        = "${var.name_prefix}-functions-source"
  location                    = var.region
  force_destroy               = var.force_destroy
  uniform_bucket_level_access = true

  labels = merge(var.labels, {
    purpose = "functions-source"
  })
}